"""Transaction, valuation, deduction, intelligence, and offline sync schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class DeductionPayload(BaseModel):
    deduction_type: str = Field(default="melting_refining", max_length=48)
    label: str = Field(min_length=2, max_length=160)
    amount_inr: Decimal = Field(ge=Decimal("0.00"))
    reason: Optional[str] = Field(default="", max_length=500)
    supporting_doc_ref: Optional[str] = Field(default=None, max_length=120)


class ValuationPreviewRequest(BaseModel):
    gross_weight_g: Decimal = Field(gt=Decimal("0"))
    non_gold_weight_g: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    net_gold_weight_g: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    purity_pct: Decimal = Field(gt=Decimal("0"), le=Decimal("100"))
    measurement_source: Literal["instrument", "manual", "simulated_demo"] = "manual"
    instrument_name: Optional[str] = Field(default=None, max_length=160)
    test_report_ref: Optional[str] = Field(default=None, max_length=120)
    rate_24k_per_g: Decimal = Field(gt=Decimal("0"))
    rate_source: str = Field(default="Shop Rate Board", min_length=2, max_length=160)
    benchmark_reference_rate_per_g: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    deductions: list[DeductionPayload] = Field(default_factory=list)
    jeweller_offered_value_inr: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    offer_difference_explanation: Optional[str] = Field(default=None, max_length=500)
    is_demo: bool = False


class TransactionCreateRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=160)
    customer_mobile: str = Field(min_length=8, max_length=20)
    customer_preferred_language: Literal["en", "ta"] = "en"
    consent_granted: bool

    item_description: str = Field(min_length=2, max_length=300)
    category: str = Field(default="ornament", max_length=64)
    hallmark_huid: Optional[str] = Field(default=None, max_length=32)
    stone_or_non_gold_description: Optional[str] = Field(default=None, max_length=200)

    gross_weight_g: Decimal = Field(gt=Decimal("0"))
    non_gold_weight_g: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    net_gold_weight_g: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    purity_pct: Decimal = Field(gt=Decimal("0"), le=Decimal("100"))
    purity_karat_label: str = Field(default="22K (916)", max_length=32)
    measurement_source: Literal["instrument", "manual", "simulated_demo"] = "manual"
    instrument_name: Optional[str] = Field(default=None, max_length=160)
    test_report_ref: Optional[str] = Field(default=None, max_length=120)
    measured_at: Optional[datetime] = None
    ocr_extracted: bool = False

    rate_24k_per_g: Decimal = Field(gt=Decimal("0"))
    rate_source: str = Field(min_length=2, max_length=160)
    rate_timestamp: Optional[datetime] = None
    benchmark_reference_rate_per_g: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    is_simulated_rate: bool = False

    deductions: list[DeductionPayload] = Field(default_factory=list)
    jeweller_offered_value_inr: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    offer_difference_explanation: Optional[str] = Field(default=None, max_length=500)

    notes: Optional[str] = Field(default=None, max_length=1000)
    is_demo: bool = False
    client_draft_id: Optional[str] = Field(default=None, max_length=64)
    client_updated_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_weights_and_consent(self) -> "TransactionCreateRequest":
        if not self.consent_granted:
            raise ValueError("Explicit customer consent must be granted before recording a gold exchange transaction.")
        if self.non_gold_weight_g > self.gross_weight_g:
            raise ValueError("Non-gold component weight cannot exceed gross weight.")
        return self


class AcknowledgeRequest(BaseModel):
    method: str = Field(default="in_app_confirmation", max_length=48)
    note: Optional[str] = Field(default=None, max_length=500)


class AmendTransactionRequest(BaseModel):
    amendment_reason: str = Field(min_length=5, max_length=500)
    updated_payload: TransactionCreateRequest


class OfflineDraftSyncItem(BaseModel):
    client_draft_id: str = Field(min_length=4, max_length=64)
    client_updated_at: datetime
    payload: TransactionCreateRequest


class OfflineSyncBatchRequest(BaseModel):
    drafts: list[OfflineDraftSyncItem] = Field(min_length=1, max_length=50)


class OfflineSyncResultItem(BaseModel):
    client_draft_id: str
    status: Literal[
        "created",
        "updated",
        "already_synced",
        "conflict_signed_immutable",
        "conflict_server_newer",
        "validation_error",
    ]
    transaction_id: Optional[str] = None
    transaction_code: Optional[str] = None
    message: str


class OfflineSyncBatchResponse(BaseModel):
    results: list[OfflineSyncResultItem]


class AnomalyFlagOut(BaseModel):
    id: str
    detection_method: str
    code: str
    severity: str
    title: str
    message: str
    evidence: dict[str, Any]
    is_resolved: bool


class ValuationPreviewResponse(BaseModel):
    gross_weight_g: str
    non_gold_weight_g: str
    net_gold_weight_g: str
    purity_pct: str
    pure_gold_weight_g: str
    rate_24k_per_g: str
    gross_reference_value_inr: str
    total_deductions_inr: str
    calculated_net_value_inr: str
    jeweller_offered_value_inr: str
    offer_difference_inr: str
    assumptions: dict[str, Any]
    calculation_steps: list[dict[str, Any]]
    flags: list[dict[str, Any]]
    ml_status: dict[str, Any]
    requires_review: bool
