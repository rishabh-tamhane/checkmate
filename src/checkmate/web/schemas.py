"""Pydantic schemas owned by the HTTP boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Public process-health response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    version: str


class ErrorDetail(BaseModel):
    """Safe details for an unexpected HTTP failure."""

    model_config = ConfigDict(extra="forbid")

    code: Literal["internal_error"]
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    """Stable envelope for unexpected HTTP failures."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail
