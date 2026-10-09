
import os

from google import genai
from google.genai import types


SYSTEM_PROMPT = """You are HerHealth's supportive, evidence-based sexual and reproductive health educator for young women.

TONE AND READING LEVEL
- Warm, non-judgmental, and reassuring. Plain language at about a 7th-8th grade reading level.
- Explain any medical term briefly the first time you use it. Never shame or moralise.

HARD RULES
- Never diagnose, prescribe medication, recommend dosages, or create treatment plans.
- Use only the supplied trusted context for medical facts. Do not invent facts or sources.
- Ground every medical statement in the trusted context: draw on it actively, restate its specific points in your own words, and prefer its details over generic knowledge.
- If the context only partly answers the question, answer the covered parts and say plainly which part is not covered. Only say the context is insufficient if it is truly unrelated.
- Suggest asking a healthcare professional for anything not covered.
- Always include red-flag guidance: say when symptoms need prompt or urgent medical care.
- Do not infer identity or request unnecessary personal information.
- Use earlier conversation only to understand follow-ups, never as a source of medical facts.

CLARIFYING QUESTIONS
- If the question is ambiguous and the answer depends on missing details, do not guess.
- Ask one or two short clarifying questions instead of giving the full format, optionally with a brief general note.

ANSWER FORMAT (keep under 200 words, scannable)
**Short answer:** one or two direct sentences.
**What's normal:** a few short bullets.
**What to watch for:** a few short bullets.
**When to see a doctor:** clear red flags and when to seek care.

Follow these instructions in the user's selected response language.
"""


TEMPERATURE = 0.3
MAX_OUTPUT_TOKENS = 700
RECENT_TURNS = 4
SUMMARY_CHARS_PER_TURN = 120


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_history(history: list[dict[str, str]] | None) -> str:
    """Keep recent turns and summarize older conversation."""
    if not history:
        return ""

    older = history[:-RECENT_TURNS]
    recent = history[-RECENT_TURNS:]
    parts = []

    if older:
        summary = "; ".join(
            f"{turn['role']}: {_clip(turn['content'], SUMMARY_CHARS_PER_TURN)}"
            for turn in older
        )
        parts.append(f"Summary of earlier conversation: {summary}")

    if recent:
        parts.append(
            "Recent conversation:\n"
            + "\n".join(
                f"{turn['role']}: {_clip(turn['content'], 500)}"
                for turn in recent
            )
        )

    return "\n\n".join(parts)


async def generate_answer(
    question: str,
    context: str,
    language: str = "English",
    history: list[dict[str, str]] | None = None,
    personal_context: str = "",
) -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    model = "gemini-3.5-flash-lite"

    try:
        client = genai.Client(api_key=api_key)

        history_text = format_history(history)
        history_block = (
            f"Earlier conversation, for context only:\n{history_text}\n\n"
            if history_text
            else ""
        )

        prompt = f"""Response language: {language}

IMPORTANT LANGUAGE INSTRUCTION:
- Write the entire answer in {language}, regardless of the question's language.
- For Hindi, use natural Hindi in Devanagari script.
- For Marathi, use natural Marathi in Devanagari script.
- Explain medical terms simply in the selected language.
- Keep source URLs unchanged. Do not invent sources.
- Do not copy English source text verbatim when answering in Hindi or Marathi.

Trusted medical context:
{context}

{history_block}{personal_context}Current user question:
{question}

First identify which parts of the trusted medical context are relevant to the
question, then build the answer from them. Answer using only the trusted
medical context for medical facts.
Use earlier conversation only to understand follow-up questions.
Use general user context only to tailor tone and relevance, never to diagnose.
Do not diagnose, prescribe, or recommend medication dosages.
If the context covers only part of the question, answer that part and say in {language} what is not covered.
Follow the answer format when appropriate, and ask a brief clarifying
question if important details are missing.
"""

        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=TEMPERATURE,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )

        answer = response.text

        if not answer or not answer.strip():
            raise ValueError("Gemini returned an empty answer.")

        return answer.strip()

    except Exception as error:
        print("GEMINI ERROR:", repr(error))
        raise ValueError("Gemini request failed.") from error
