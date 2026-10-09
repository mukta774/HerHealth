from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class NmcSearchRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    registration_number: str | None = Field(default=None, max_length=80)
    council: str | None = Field(default=None, max_length=120)

    @field_validator("name", "registration_number", "council", mode="before")
    @classmethod
    def clean_search_value(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Search values must be text.")
        value = value.strip()
        if any(ord(character) < 32 for character in value):
            raise ValueError("Search values must not contain control characters.")
        return value or None

    @model_validator(mode="after")
    def require_search_term(self) -> "NmcSearchRequest":
        if not any((self.name, self.registration_number, self.council)):
            raise ValueError("Provide a doctor's name, registration number, or council.")
        return self


class NmcDoctorResult(BaseModel):
    name: str | None = None
    registration_number: str | None = None
    council: str | None = None
    registration_date: str | None = None
    qualification: str | None = None
    registration_status: str | None = None
    source_url: HttpUrl | None = None
    retrieved_at: datetime
    verification_status: str = "unverified"


class NmcLookupResponse(BaseModel):
    results: list[NmcDoctorResult]
    retrieved_at: datetime
    verification_notice: str = (
        "These results are unverified source data, not official confirmation "
        "of registration. A missing result does not prove that a doctor is unregistered."
    )
