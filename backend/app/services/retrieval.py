import json
import re
from pathlib import Path


_CORPUS_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "health.json"
_TOKEN_PATTERN = re.compile(r"[a-z]{3,}")
_STOP_WORDS = {
    "about", "after", "also", "and", "are", "been", "before", "being", "can",
    "could", "does", "for", "from", "have", "help", "how", "into", "just",
    "like", "many", "more", "most", "much", "over", "same", "should", "some",
    "that", "them", "then", "there", "these", "they", "this", "those", "what",
    "when", "where", "which", "while", "with", "would", "your",
}
_TRANSLATION_KEYWORDS = {
    # Marathi
    "पाळी": "period menstrual",
    "मासिक": "period menstrual",
    "अनियमित": "irregular",
    "कारणे": "causes reasons",
    "कारण": "cause reason",
    "गर्भधारणा": "pregnancy",
    "गर्भवती": "pregnant",
    "दुखणे": "pain",
    "वेदना": "pain",
    "रक्तस्राव": "bleeding",
    "चिंता": "anxiety stress",
    "तणाव": "stress",
    "अंडाशय": "ovary",
    "पीसीओएस": "pcos polycystic ovary syndrome",

    # Hindi
    "पीरियड": "period menstrual",
    "मासिक": "period menstrual",
    "अनियमित": "irregular",
    "कारण": "cause reasons",
    "गर्भावस्था": "pregnancy",
    "दर्द": "pain",
    "खून": "bleeding",
    "रक्तस्राव": "bleeding",
    "तनाव": "stress",
    "चिंता": "anxiety stress",
}


def _stem(token: str) -> str:
    for suffix in ("ing", "ies", "es", "ed", "s", "al", "ly"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def _tokens(text: str) -> set[str]:
    return {
        _stem(token)
        for token in _TOKEN_PATTERN.findall(text)
        if token not in _STOP_WORDS
    }


def _load_documents() -> list[dict[str, str]]:
    with _CORPUS_PATH.open(encoding="utf-8") as corpus_file:
        documents = json.load(corpus_file)
    if not isinstance(documents, list):
        raise ValueError("The health knowledge corpus must be a list.")
    return documents


def retrieve(question: str, limit: int = 3) -> list[dict[str, str]]:
    expanded_question = question.lower()

    for word, translation in _TRANSLATION_KEYWORDS.items():
        if word in expanded_question:
            expanded_question += f" {translation}"

    query_terms = _tokens(expanded_question)

    if not query_terms:
        return []

    ranked: list[tuple[int, dict[str, str]]] = []

    for document in _load_documents():
        document_text = (
            f"{document['title']} "
            f"{document['keywords']} "
            f"{document['content']}"
        ).lower()

        document_terms = _tokens(document_text)

        score = len(query_terms & document_terms)

        if score:
            ranked.append((score, document))

    ranked.sort(key=lambda item: item[0], reverse=True)

    return [document for _, document in ranked[:limit]]