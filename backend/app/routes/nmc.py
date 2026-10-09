from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.nmc import NmcLookupResponse, NmcSearchRequest
from app.services.nmc_lookup import (
    NmcApifyTimeoutError,
    NmcConfigurationError,
    NmcLookupError,
    lookup_doctors,
)

router = APIRouter()


@router.post("/api/doctors/registration-lookup")
async def lookup_registration(
    request: NmcSearchRequest,
) -> NmcLookupResponse | JSONResponse:
    try:
        results = await lookup_doctors(request)
    except NmcConfigurationError as error:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "lookup_not_configured", "message": str(error)}},
        )
    except NmcApifyTimeoutError as error:
        return JSONResponse(
            status_code=504,
            content={"error": {"code": "lookup_timeout", "message": str(error)}},
        )
    except NmcLookupError:
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "code": "lookup_unavailable",
                    "message": "Registration lookup is temporarily unavailable. Please try again.",
                }
            },
        )

    retrieved_at = results[0].retrieved_at if results else datetime.now(UTC)
    return NmcLookupResponse(results=results, retrieved_at=retrieved_at)
