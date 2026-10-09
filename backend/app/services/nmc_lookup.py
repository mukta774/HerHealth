import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.models.nmc import NmcDoctorResult, NmcSearchRequest

APIFY_API_BASE_URL = "https://api.apify.com/v2"
_CACHE_TTL_SECONDS = 60
_CACHE: dict[str, tuple[float, list[NmcDoctorResult]]] = {}
_IN_FLIGHT: dict[str, asyncio.Task[list[NmcDoctorResult]]] = {}


class NmcLookupError(Exception):
    pass


class NmcConfigurationError(NmcLookupError):
    pass


class NmcApifyError(NmcLookupError):
    pass


class NmcApifyTimeoutError(NmcLookupError):
    pass


@dataclass(frozen=True)
class ApifyConfig:
    token: str
    actor_id: str
    input_fields: dict[str, str]
    output_fields: dict[str, str]
    timeout_seconds: int = 60
    max_results: int = 100

    @classmethod
    def from_environment(cls, search: NmcSearchRequest) -> "ApifyConfig":
        token = os.getenv("APIFY_API_TOKEN", "").strip()
        actor_id = os.getenv("APIFY_ACTOR_ID", "").strip()
        if not token or not actor_id:
            raise NmcConfigurationError(
                "Doctor registration lookup is not configured."
            )

        input_fields = {
            "name": os.getenv("APIFY_INPUT_NAME_FIELD", "").strip(),
            "registration_number": os.getenv(
                "APIFY_INPUT_REGISTRATION_NUMBER_FIELD", ""
            ).strip(),
            "council": os.getenv("APIFY_INPUT_COUNCIL_FIELD", "").strip(),
        }
        output_fields = {
            "name": os.getenv("APIFY_OUTPUT_NAME_FIELD", "").strip(),
            "registration_number": os.getenv(
                "APIFY_OUTPUT_REGISTRATION_NUMBER_FIELD", ""
            ).strip(),
            "council": os.getenv("APIFY_OUTPUT_COUNCIL_FIELD", "").strip(),
            "registration_date": os.getenv(
                "APIFY_OUTPUT_REGISTRATION_DATE_FIELD", ""
            ).strip(),
            "qualification": os.getenv(
                "APIFY_OUTPUT_QUALIFICATION_FIELD", ""
            ).strip(),
            "registration_status": os.getenv(
                "APIFY_OUTPUT_REGISTRATION_STATUS_FIELD", ""
            ).strip(),
            "source_url": os.getenv("APIFY_OUTPUT_SOURCE_URL_FIELD", "").strip(),
        }
        for key, value in (
            ("name", search.name),
            ("registration_number", search.registration_number),
            ("council", search.council),
        ):
            if value and not input_fields[key]:
                raise NmcConfigurationError(
                    f"The actor input field for {key.replace('_', ' ')} is not configured."
                )
        if not output_fields["name"] and not output_fields["registration_number"]:
            raise NmcConfigurationError(
                "Configure an actor output field for the doctor's name or registration number."
            )
        try:
            timeout_seconds = int(os.getenv("APIFY_TIMEOUT_SECONDS", "60"))
            max_results = int(os.getenv("APIFY_MAX_RESULTS", "100"))
        except ValueError as error:
            raise NmcConfigurationError("Apify limits must be integers.") from error
        if timeout_seconds < 1 or max_results < 1:
            raise NmcConfigurationError("Apify limits must be positive.")
        if not all(character.isalnum() or character in "~._-" for character in actor_id):
            raise NmcConfigurationError("The configured Apify actor ID is invalid.")
        return cls(
            token=token,
            actor_id=actor_id,
            input_fields=input_fields,
            output_fields=output_fields,
            timeout_seconds=min(timeout_seconds, 180),
            max_results=min(max_results, 500),
        )

    def actor_input(self, search: NmcSearchRequest) -> dict[str, str]:
        return {
            self.input_fields[key]: value
            for key, value in (
                ("name", search.name),
                ("registration_number", search.registration_number),
                ("council", search.council),
            )
            if value
        }


class ApifyNmcLookup:
    def __init__(
        self,
        config: ApifyConfig,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=APIFY_API_BASE_URL,
            headers={
                "Authorization": "Bearer " + config.token,
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(10),
            transport=transport,
        )

    async def lookup(self, search: NmcSearchRequest) -> list[NmcDoctorResult]:
        try:
            return await asyncio.wait_for(
                self._run_and_collect(search),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError as error:
            raise NmcApifyTimeoutError(
                "The registration search timed out. Please try again."
            ) from error
        except httpx.TimeoutException as error:
            raise NmcApifyTimeoutError(
                "The registration search timed out. Please try again."
            ) from error
        except httpx.HTTPStatusError as error:
            raise NmcApifyError(
                "The registration search service returned an error."
            ) from error
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise NmcApifyError(
                "The registration search service returned an invalid response."
            ) from error
        finally:
            await self._client.aclose()

    async def _run_and_collect(
        self, search: NmcSearchRequest
    ) -> list[NmcDoctorResult]:
        actor_id = quote(self.config.actor_id, safe="~")
        run_response = await self._request(
            "POST",
            f"/acts/{actor_id}/runs",
            json=self.config.actor_input(search),
        )
        run = self._data(run_response)
        run_id = run.get("id")
        if not isinstance(run_id, str) or not run_id:
            raise NmcApifyError("The actor did not return a run ID.")

        deadline = time.monotonic() + self.config.timeout_seconds
        dataset_id = run.get("defaultDatasetId")
        status = run.get("status")
        while status not in {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise NmcApifyTimeoutError(
                    "The registration search timed out. Please try again."
                )
            await asyncio.sleep(min(1, remaining))
            run_response = await self._request(
                "GET", f"/actor-runs/{quote(run_id, safe='')}"
            )
            run = self._data(run_response)
            status = run.get("status")
            dataset_id = run.get("defaultDatasetId") or dataset_id

        if status != "SUCCEEDED":
            raise NmcApifyError("The registration search could not be completed.")
        if not isinstance(dataset_id, str) or not dataset_id:
            raise NmcApifyError("The completed actor run did not provide a dataset.")

        items = await self._dataset_items(dataset_id)
        retrieved_at = datetime.now(UTC)
        return [
            self._normalize(item, retrieved_at)
            for item in items[: self.config.max_results]
            if isinstance(item, dict)
        ]

    async def _dataset_items(self, dataset_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_size = min(100, self.config.max_results)
        offset = 0
        while offset < self.config.max_results:
            page = await self._request(
                "GET",
                f"/datasets/{quote(dataset_id, safe='')}/items",
                params={
                    "format": "json",
                    "limit": min(page_size, self.config.max_results - offset),
                    "offset": offset,
                },
            )
            if not isinstance(page, list):
                raise NmcApifyError("The actor dataset was not a list of records.")
            items.extend(item for item in page if isinstance(item, dict))
            if len(page) < page_size:
                break
            offset += len(page)
        return items

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _data(response: Any) -> dict[str, Any]:
        if not isinstance(response, dict) or not isinstance(
            response.get("data"), dict
        ):
            raise NmcApifyError("The actor returned an invalid response.")
        return response["data"]

    def _normalize(
        self, item: dict[str, Any], retrieved_at: datetime
    ) -> NmcDoctorResult:
        normalized: dict[str, Any] = {
            field: self._text(item.get(actor_field))
            for field, actor_field in self.config.output_fields.items()
            if actor_field
        }
        source_url = normalized.get("source_url")
        if source_url and not source_url.lower().startswith(("https://", "http://")):
            normalized["source_url"] = None
        normalized["retrieved_at"] = retrieved_at
        normalized["verification_status"] = "unverified"
        return NmcDoctorResult(**normalized)

    @staticmethod
    def _text(value: Any) -> str | None:
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            return None
        text = str(value).strip()
        return text[:500] or None


async def lookup_doctors(search: NmcSearchRequest) -> list[NmcDoctorResult]:
    config = ApifyConfig.from_environment(search)
    cache_key = hashlib.sha256(
        json.dumps(
            {
                "search": search.model_dump(),
                "actor_id": config.actor_id,
                "input_fields": config.input_fields,
                "output_fields": config.output_fields,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    cached = _CACHE.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    if cached:
        _CACHE.pop(cache_key, None)

    task = _IN_FLIGHT.get(cache_key)
    if task is None:
        task = asyncio.create_task(_lookup_and_cache(cache_key, config, search))
        _IN_FLIGHT[cache_key] = task
        task.add_done_callback(
            lambda completed: _IN_FLIGHT.pop(cache_key, None)
            if _IN_FLIGHT.get(cache_key) is completed
            else None
        )
    return await asyncio.shield(task)


async def _lookup_and_cache(
    cache_key: str, config: ApifyConfig, search: NmcSearchRequest
) -> list[NmcDoctorResult]:
    service = ApifyNmcLookup(config)
    results = await service.lookup(search)
    _CACHE[cache_key] = (time.monotonic() + _CACHE_TTL_SECONDS, results)
    return results
