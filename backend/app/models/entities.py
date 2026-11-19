"""ORM entity definitions for all 14 GoldProof relational tables."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Stores UTC timestamps and always returns timezone-aware UTC datetimes on SQLite & Postgres."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


# 1. users
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False, index=True)  # jeweller | customer | admin
    preferred_language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now)

    jeweller_profile: Mapped[Optional["JewellerProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    customer_profiles: Mapped[list["CustomerProfile"]] = relationship(
        back_populates="user", foreign_keys="CustomerProfile.user_id"
    )


# 2. jeweller_profiles
class JewellerProfile(Base):
    __tablename__ = "jeweller_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False)
    shop_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Coimbatore")
    state: Mapped[str] = mapped_column(String(100), nullable=False, default="Tamil Nadu")
    gstin: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    bis_hallmark_license: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    policy_max_deduction_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("5.00"))
    policy_max_wastage_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("3.00"))
    policy_max_fixed_deduction_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("5000.00"))
    policy_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valuation_conventions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship(back_populates="jeweller_profile")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="jeweller")


# 3. customer_profiles
class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    jeweller_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("jeweller_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    mobile_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    preferred_language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user: Mapped[Optional["User"]] = relationship(back_populates="customer_profiles", foreign_keys=[user_id])
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="customer_profile")


# 4. transactions
class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_jeweller_status", "jeweller_id", "status"),
        Index("ix_transactions_jeweller_created", "jeweller_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False, index=True)
    jeweller_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jeweller_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customer_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_acknowledgement", index=True
    )  # draft | pending_review | pending_acknowledgement | signed | amended | cancelled
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amendment_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_draft_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    client_updated_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now)

    jeweller: Mapped["JewellerProfile"] = relationship(back_populates="transactions")
    customer_profile: Mapped["CustomerProfile"] = relationship(back_populates="transactions")
    parent_transaction: Mapped[Optional["Transaction"]] = relationship(
        remote_side=[id], foreign_keys=[parent_transaction_id]
    )
    jewellery_items: Mapped[list["JewelleryItem"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    measurement_record: Mapped[Optional["MeasurementRecord"]] = relationship(
        back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )
    rate_record: Mapped[Optional["RateRecord"]] = relationship(
        back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )
    deductions: Mapped[list["Deduction"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    valuation_result: Mapped[Optional["ValuationResult"]] = relationship(
        back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )
    anomaly_flags: Mapped[list["AnomalyFlag"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    acknowledgements: Mapped[list["Acknowledgement"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    digital_passport: Mapped[Optional["DigitalPassport"]] = relationship(
        back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )
    consent_records: Mapped[list["ConsentRecord"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )


# 5. jewellery_items
class JewelleryItem(Base):
    __tablename__ = "jewellery_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_description: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="ornament")
    hallmark_huid: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    stone_or_non_gold_description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)

    transaction: Mapped["Transaction"] = relationship(back_populates="jewellery_items")


# 6. measurement_records
class MeasurementRecord(Base):
    __tablename__ = "measurement_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    gross_weight_g: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    non_gold_weight_g: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0.0000"))
    net_gold_weight_g: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    purity_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    purity_karat_label: Mapped[str] = mapped_column(String(32), nullable=False, default="22K")
    measurement_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual"
    )  # instrument | manual | simulated_demo
    instrument_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    test_report_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    measured_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    ocr_extracted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ocr_confirmed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)

    transaction: Mapped["Transaction"] = relationship(back_populates="measurement_record")


# 7. rate_records
class RateRecord(Base):
    __tablename__ = "rate_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    rate_24k_per_g: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    rate_source: Mapped[str] = mapped_column(String(160), nullable=False)
    rate_timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    benchmark_reference_rate_per_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    is_simulated_rate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)

    transaction: Mapped["Transaction"] = relationship(back_populates="rate_record")


# 8. deductions
class Deduction(Base):
    __tablename__ = "deductions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deduction_type: Mapped[str] = mapped_column(String(48), nullable=False, default="other")
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    percentage_of_gross: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("0.00"))
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supporting_doc_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)

    transaction: Mapped["Transaction"] = relationship(back_populates="deductions")


# 9. valuation_results
class ValuationResult(Base):
    __tablename__ = "valuation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    pure_gold_weight_g: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    gross_reference_value_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_deductions_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    calculated_net_value_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    jeweller_offered_value_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    offer_difference_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    offer_difference_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assumptions_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    calculation_steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)

    transaction: Mapped["Transaction"] = relationship(back_populates="valuation_result")


# 10. anomaly_flags
class AnomalyFlag(Base):
    __tablename__ = "anomaly_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    detection_method: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # rule_based | ml_isolation_forest
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)  # info | attention | review_required
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)

    transaction: Mapped["Transaction"] = relationship(back_populates="anomaly_flags")


# 11. acknowledgements
class Acknowledgement(Base):
    __tablename__ = "acknowledgements"
    __table_args__ = (UniqueConstraint("transaction_id", "party_role", name="uq_ack_tx_party"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    party_role: Mapped[str] = mapped_column(String(24), nullable=False)  # jeweller | customer
    acknowledged_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    acknowledged_by_name: Mapped[str] = mapped_column(String(160), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    method: Mapped[str] = mapped_column(String(48), nullable=False, default="in_app_confirmation")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="acknowledgements")


# 12. digital_passports
class DigitalPassport(Base):
    __tablename__ = "digital_passports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    transaction_code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_passport_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    canonical_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signature_algorithm: Mapped[str] = mapped_column(String(32), nullable=False, default="Ed25519")
    signature_b64: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_b64: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_url: Mapped[str] = mapped_column(String(500), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    is_revoked_by_amendment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    transaction: Mapped["Transaction"] = relationship(back_populates="digital_passport")


# 13. audit_logs (append-only hash chain)
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    sequence_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    jeweller_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("jeweller_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_role: Mapped[str] = mapped_column(String(24), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    previous_log_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)


# 14. consent_records
class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_type: Mapped[str] = mapped_column(String(48), nullable=False, default="transaction_recording")
    consent_granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_text_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.0-en-ta")
    captured_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    captured_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    transaction: Mapped["Transaction"] = relationship(back_populates="consent_records")
