"""Pydantic schemas owned by the HTTP boundary."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

STRICT_SCHEMA = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class HealthResponse(BaseModel):
    """Public process-health response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    version: str


class ErrorDetail(BaseModel):
    """Safe details for an unexpected HTTP failure."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    """Stable envelope for unexpected HTTP failures."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


class ReceiptItemRequest(BaseModel):
    """One raw editable receipt row."""

    model_config = STRICT_SCHEMA

    id: str
    name: str
    quantity: str
    line_total: str = Field(alias="lineTotal")


class ReceiptRequest(BaseModel):
    """Raw editable receipt fields."""

    model_config = STRICT_SCHEMA

    restaurant_name: str = Field(alias="restaurantName")
    date: str
    items: list[ReceiptItemRequest]
    subtotal: str
    tax: str
    tip: str
    total: str


class ParticipantRequest(BaseModel):
    """One raw editable participant."""

    model_config = STRICT_SCHEMA

    id: str
    name: str


class CalculationRequest(BaseModel):
    """The complete stateless draft for one client revision."""

    model_config = STRICT_SCHEMA

    revision: Annotated[int, Field(ge=0)]
    receipt: ReceiptRequest
    participants: list[ParticipantRequest]
    assignments: dict[str, list[str]]


class ValidationIssueResponse(BaseModel):
    """A browser-renderable validation issue."""

    model_config = STRICT_SCHEMA

    code: str
    path: str
    message: str
    severity: Literal["error", "warning"]


class NormalizedReceiptItemResponse(BaseModel):
    """One successfully normalized item."""

    model_config = STRICT_SCHEMA

    id: str
    name: str
    quantity: str | None
    line_total: str = Field(alias="lineTotal")


class NormalizedReceiptResponse(BaseModel):
    """Successfully normalized receipt values."""

    model_config = STRICT_SCHEMA

    restaurant_name: str | None = Field(alias="restaurantName")
    date: str | None
    items: list[NormalizedReceiptItemResponse]
    subtotal: str
    tax: str
    tip: str
    total: str


class NormalizedParticipantResponse(BaseModel):
    """One successfully normalized participant."""

    model_config = STRICT_SCHEMA

    id: str
    name: str


class NormalizedDraftResponse(BaseModel):
    """Canonical values used by the domain calculation."""

    model_config = STRICT_SCHEMA

    receipt: NormalizedReceiptResponse
    participants: list[NormalizedParticipantResponse]
    assignments: dict[str, list[str]]


class ParticipantShareResponse(BaseModel):
    """One formatted participant share of an item."""

    model_config = STRICT_SCHEMA

    participant_id: str = Field(alias="participantId")
    amount: str


class ItemAllocationResponse(BaseModel):
    """Formatted allocation for one item."""

    model_config = STRICT_SCHEMA

    item_id: str = Field(alias="itemId")
    shares: list[ParticipantShareResponse]


class ParticipantTotalResponse(BaseModel):
    """Formatted participant summary in deterministic order."""

    model_config = STRICT_SCHEMA

    participant_id: str = Field(alias="participantId")
    name: str
    item_subtotal: str = Field(alias="itemSubtotal")
    tax: str
    tip: str
    total: str


class ReconciliationComponentResponse(BaseModel):
    """Entered, calculated, and signed difference for one total."""

    model_config = STRICT_SCHEMA

    entered: str
    calculated: str
    difference: str


class ReconciliationResponse(BaseModel):
    """Receipt subtotal and total reconciliation."""

    model_config = STRICT_SCHEMA

    subtotal: ReconciliationComponentResponse
    total: ReconciliationComponentResponse


class CalculationResponse(BaseModel):
    """Complete response for a structurally valid editable draft."""

    model_config = STRICT_SCHEMA

    revision: int
    normalized: NormalizedDraftResponse | None
    issues: list[ValidationIssueResponse]
    item_allocations: list[ItemAllocationResponse] = Field(alias="itemAllocations")
    participant_totals: list[ParticipantTotalResponse] = Field(
        alias="participantTotals"
    )
    reconciliation: ReconciliationResponse | None
    finalized: bool
    non_zero: bool = Field(alias="nonZero")
