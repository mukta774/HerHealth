import asyncio

import httpx
import pytest

from app.main import app
from app.models.nmc import NmcSearchRequest
from app.routes import nmc as nmc_route
from app.services import nmc_lookup
from app.services.nmc_lookup import (
    ApifyConfig,
    ApifyNmcLookup,
    NmcApifyError,
    NmcApifyTimeoutError,
    NmcConfigurationError,
)
from fastapi.testclient import TestClient

client = TestClient(app)


def test_missing_apify_configuration_is_reported(monkeypatch) -> None:
    monkeypatch.delenv("APIFY_API_TOKEN", raising=False)
    monkeypatch.delenv("APIFY_ACTOR_ID", raising=False)

    with pytest.raises(NmcConfigurationError):
        ApifyConfig.from_environment(NmcSearchRequest(name="Dr. Example"))


def test_actor_input_fields_are_configurable() -> None:
    config = ApifyConfig(
        token="test-token",
        actor_id="account~actor",
        input_fields={
            "name": "doctorName",
            "registration_number": "registrationId",
            "council": "medicalCouncil",
        },
        output_fields={"name": "fullName", "registration_number": "regNo"},
    )

    assert config.actor_input(
        NmcSearchRequest(name="  Dr. Example ", registration_number="REG-123")
    ) == {"doctorName": "Dr. Example", "registrationId": "REG-123"}


def test_search_requires_at_least_one_nonblank_value() -> None:
    with pytest.raises(ValueError):
        NmcSearchRequest(name=" ", registration_number="", council=None)


def _config(max_results: int = 100) -> ApifyConfig:
    return ApifyConfig(
        token="test-token",
        actor_id="account~actor",
        input_fields={
            "name": "name",
            "registration_number": "registrationId",
            "council": "stateMedicalCouncil",
        },
        output_fields={
            "name": "doctorName",
            "registration_number": "regNo",
            "council": "council",
            "registration_date": "registeredOn",
            "qualification": "qualification",
            "registration_status": "status",
            "source_url": "sourceUrl",
        },
        timeout_seconds=10,
        max_results=max_results,
    )


def test_successful_run_polls_and_reads_paginated_dataset(monkeypatch) -> None:
    dataset_pages = {
        "0": [
            {
                "doctorName": "Dr. A",
                "regNo": "100",
                "council": "Council A",
                "registeredOn": "2020-01-01",
                "qualification": "MBBS",
                "status": "Active",
                "sourceUrl": "https://register.example/100",
            }
            for _ in range(100)
        ],
        "100": [
            {"doctorName": "Dr. B", "regNo": "200", "sourceUrl": "javascript:alert(1)"}
        ],
    }
    calls: list[httpx.Request] = []
    statuses = iter(["RUNNING", "SUCCEEDED"])

    async def skip_poll_delay(_seconds: float) -> None:
        return None

    monkeypatch.setattr(nmc_lookup.asyncio, "sleep", skip_poll_delay)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "data": {
                        "id": "run-id",
                        "status": "RUNNING",
                    }
                },
            )
        if request.url.path.endswith("/actor-runs/run-id"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "run-id",
                        "status": next(statuses),
                        "defaultDatasetId": "dataset-id",
                    }
                },
            )
        if request.url.path.endswith("/items"):
            offset = request.url.params.get("offset", "0")
            return httpx.Response(200, json=dataset_pages[offset])
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    async def perform_lookup():
        service = ApifyNmcLookup(_config(max_results=150), httpx.MockTransport(handler))
        return await service.lookup(NmcSearchRequest(name="Dr"))

    results = asyncio.run(perform_lookup())

    assert len(results) == 101
    assert results[0].registration_number == "100"
    assert results[0].verification_status == "unverified"
    assert str(results[0].source_url) == "https://register.example/100"
    assert results[-1].name == "Dr. B"
    assert results[-1].source_url is None
    dataset_calls = [call for call in calls if call.url.path.endswith("/items")]
    assert [call.url.params["offset"] for call in dataset_calls] == ["0", "100"]
    assert calls[0].headers["Authorization"] == "Bearer " + "test-" + "token"


def test_actor_failed_run_returns_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={
                "data": {
                    "id": "run-id",
                    "status": "FAILED",
                    "defaultDatasetId": "dataset-id",
                }
            },
        )

    async def perform_lookup():
        service = ApifyNmcLookup(_config(), httpx.MockTransport(handler))
        return await service.lookup(NmcSearchRequest(name="Dr"))

    with pytest.raises(NmcApifyError):
        asyncio.run(perform_lookup())


def test_actor_timeout_is_reported() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.1)
        return httpx.Response(
            201,
            json={
                "data": {
                    "id": "run-id",
                    "status": "SUCCEEDED",
                    "defaultDatasetId": "dataset-id",
                }
            },
        )

    async def perform_lookup():
        config = ApifyConfig(**{**_config().__dict__, "timeout_seconds": 0.01})
        service = ApifyNmcLookup(config, httpx.MockTransport(handler))
        return await service.lookup(NmcSearchRequest(name="Dr"))

    with pytest.raises(NmcApifyTimeoutError):
        asyncio.run(perform_lookup())


def test_no_results_and_malformed_fields_are_handled() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "data": {
                        "id": "run-id",
                        "status": "SUCCEEDED",
                        "defaultDatasetId": "dataset-id",
                    }
                },
            )
        return httpx.Response(
            200,
            json=[
                {
                    "doctorName": None,
                    "regNo": {"unexpected": "object"},
                    "registeredOn": 20200101,
                    "sourceUrl": "not-a-url",
                },
                None,
            ],
        )

    async def perform_lookup():
        service = ApifyNmcLookup(_config(), httpx.MockTransport(handler))
        return await service.lookup(NmcSearchRequest(registration_number="REG-123"))

    results = asyncio.run(perform_lookup())
    assert len(results) == 1
    assert results[0].name is None
    assert results[0].registration_number is None
    assert results[0].registration_date == "20200101"
    assert results[0].source_url is None

    def empty_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "data": {
                        "id": "run-id",
                        "status": "SUCCEEDED",
                        "defaultDatasetId": "dataset-id",
                    }
                },
            )
        return httpx.Response(200, json=[])

    async def perform_empty_lookup():
        service = ApifyNmcLookup(_config(), httpx.MockTransport(empty_handler))
        return await service.lookup(NmcSearchRequest(name="No match"))

    assert asyncio.run(perform_empty_lookup()) == []


def test_lookup_endpoint_validates_input_and_returns_structured_errors(monkeypatch) -> None:
    invalid_response = client.post("/api/doctors/registration-lookup", json={})
    assert invalid_response.status_code == 422

    async def not_configured(_request):
        raise NmcConfigurationError("Doctor registration lookup is not configured.")

    monkeypatch.setattr(nmc_route, "lookup_doctors", not_configured)
    response = client.post(
        "/api/doctors/registration-lookup",
        json={"registration_number": "REG-123"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "lookup_not_configured"


def test_lookup_endpoint_returns_multiple_results(monkeypatch) -> None:
    async def multiple_results(_request):
        return [
            nmc_lookup.NmcDoctorResult(name="Dr. A", registration_number="100", retrieved_at="2025-01-01T00:00:00Z"),
            nmc_lookup.NmcDoctorResult(name="Dr. B", registration_number="200", retrieved_at="2025-01-01T00:00:00Z"),
        ]

    monkeypatch.setattr(nmc_route, "lookup_doctors", multiple_results)
    response = client.post(
        "/api/doctors/registration-lookup",
        json={"name": "Dr."},
    )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 2
    assert response.json()["results"][0]["verification_status"] == "unverified"


def test_lookup_endpoint_reports_upstream_failure(monkeypatch) -> None:
    async def failed(_request):
        raise NmcApifyError("upstream details must not be exposed")

    monkeypatch.setattr(nmc_route, "lookup_doctors", failed)
    response = client.post(
        "/api/doctors/registration-lookup",
        json={"name": "Dr."},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "lookup_unavailable"
    assert "upstream details" not in response.text


def test_lookup_endpoint_reports_timeout(monkeypatch) -> None:
    async def timed_out(_request):
        raise NmcApifyTimeoutError("The registration search timed out. Please try again.")

    monkeypatch.setattr(nmc_route, "lookup_doctors", timed_out)
    response = client.post(
        "/api/doctors/registration-lookup",
        json={"name": "Dr."},
    )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "lookup_timeout"


def test_duplicate_searches_share_one_actor_execution(monkeypatch) -> None:
    config = _config()
    monkeypatch.setattr(
        ApifyConfig,
        "from_environment",
        classmethod(lambda _cls, _request: config),
    )
    nmc_lookup._CACHE.clear()
    nmc_lookup._IN_FLIGHT.clear()
    calls = 0

    class FakeApifyLookup:
        def __init__(self, _config):
            pass

        async def lookup(self, _search):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)
            return []

    monkeypatch.setattr(nmc_lookup, "ApifyNmcLookup", FakeApifyLookup)

    async def perform_duplicate_lookups():
        search = NmcSearchRequest(name="Dr. Same")
        return await asyncio.gather(
            nmc_lookup.lookup_doctors(search),
            nmc_lookup.lookup_doctors(search),
        )

    assert asyncio.run(perform_duplicate_lookups()) == [[], []]
    assert calls == 1
