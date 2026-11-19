"""Idempotent demo data seeder creating clearly labelled [DEMO] users and transactions."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.entities import (
    Acknowledgement,
    AnomalyFlag,
    ConsentRecord,
    CustomerProfile,
    Deduction,
    JewellerProfile,
    JewelleryItem,
    MeasurementRecord,
    RateRecord,
    Transaction,
    User,
    ValuationResult,
)
from app.services.audit_service import record_audit_event
from app.services.deduction_intelligence import evaluate_transaction_intelligence
from app.services.passport_service import issue_digital_passport
from app.services.valuation import DeductionInput, calculate_valuation

DEMO_PASSWORD = "GoldProof2026!"


def get_demo_accounts_catalog() -> list[dict[str, str]]:
    """Return non-sensitive demo directory for 1-click development sign-in."""
    return [
        {
            "label": "Jeweller 1 — Kaveri Heritage Jewellers (Coimbatore)",
            "email": "meena@kaverigold.demo",
            "password": DEMO_PASSWORD,
            "role": "jeweller",
            "preferred_language": "en",
            "description": "Primary demo jeweller with signed, flagged, and pending-ack transactions.",
        },
        {
            "label": "Jeweller 2 — Madurai Bullion & Crafts (Tenant Isolation)",
            "email": "arun@maduraigold.demo",
            "password": DEMO_PASSWORD,
            "role": "jeweller",
            "preferred_language": "en",
            "description": "Second jeweller shop used to verify strict multi-tenant data isolation.",
        },
        {
            "label": "Customer — Lakshmi Narayanan (தமிழ் / English)",
            "email": "lakshmi@customer.demo",
            "password": DEMO_PASSWORD,
            "role": "customer",
            "preferred_language": "ta",
            "description": "Customer portal with Tamil & English voice assistant and Digital Passports.",
        },
        {
            "label": "Administrator — GoldProof Trust Ops",
            "email": "admin@goldproof.demo",
            "password": DEMO_PASSWORD,
            "role": "admin",
            "preferred_language": "en",
            "description": "Platform analytics and hash-chained append-only audit log explorer.",
        },
    ]


def _create_demo_transaction(
    db: Session,
    *,
    code: str,
    jeweller: JewellerProfile,
    jeweller_user: User,
    customer_profile: CustomerProfile,
    customer_user: Optional[User],
    item_desc: str,
    category: str,
    hallmark_huid: Optional[str],
    stone_desc: Optional[str],
    gross_w: Decimal,
    non_gold_w: Decimal,
    net_w: Decimal,
    purity_pct: Decimal,
    karat_label: str,
    measurement_source: str,
    instrument_name: Optional[str],
    test_report_ref: Optional[str],
    rate_24k: Decimal,
    rate_source: str,
    deduction_inputs: list[DeductionInput],
    offered_value: Optional[Decimal],
    offer_diff_explanation: Optional[str],
    created_at: datetime,
    jeweller_ack: bool,
    customer_ack: bool,
    issue_passport: bool,
    notes: str,
) -> Transaction:
    valuation = calculate_valuation(
        gross_weight_g=gross_w,
        non_gold_weight_g=non_gold_w,
        net_gold_weight_g=net_w,
        purity_pct=purity_pct,
        rate_24k_per_g=rate_24k,
        deductions=deduction_inputs,
        jeweller_offered_value_inr=offered_value,
        offer_difference_explanation=offer_diff_explanation,
        measurement_source=measurement_source,
        rate_source=rate_source,
        shop_conventions=jeweller.valuation_conventions,
    )

    intel = evaluate_transaction_intelligence(
        db=db,
        jeweller=jeweller,
        valuation=valuation,
        deductions=deduction_inputs,
        measurement_source=measurement_source,
        instrument_name=instrument_name,
        test_report_ref=test_report_ref,
        benchmark_reference_rate_per_g=Decimal("7600.00"),
        offer_difference_explanation=offer_diff_explanation,
        is_demo=True,
    )

    status = "pending_review" if intel.requires_review else "pending_acknowledgement"

    tx = Transaction(
        transaction_code=code,
        jeweller_id=jeweller.id,
        customer_profile_id=customer_profile.id,
        customer_user_id=customer_user.id if customer_user else None,
        status=status,
        version_number=1,
        is_demo=True,
        notes=notes,
        created_by_user_id=jeweller_user.id,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(tx)
    db.flush()

    db.add(
        JewelleryItem(
            transaction_id=tx.id,
            item_description=item_desc,
            category=category,
            hallmark_huid=hallmark_huid,
            stone_or_non_gold_description=stone_desc,
            created_at=created_at,
        )
    )
    db.add(
        MeasurementRecord(
            transaction_id=tx.id,
            gross_weight_g=valuation.gross_weight_g,
            non_gold_weight_g=valuation.non_gold_weight_g,
            net_gold_weight_g=valuation.net_gold_weight_g,
            purity_pct=valuation.purity_pct,
            purity_karat_label=karat_label,
            measurement_source=measurement_source,
            instrument_name=instrument_name,
            test_report_ref=test_report_ref,
            measured_at=created_at,
            ocr_extracted=False,
            created_at=created_at,
        )
    )
    db.add(
        RateRecord(
            transaction_id=tx.id,
            rate_24k_per_g=valuation.rate_24k_per_g,
            rate_source=rate_source,
            rate_timestamp=created_at,
            benchmark_reference_rate_per_g=Decimal("7600.00"),
            is_simulated_rate=True,
            created_at=created_at,
        )
    )
    for d_in, pct in zip(deduction_inputs, valuation.deduction_percentages):
        db.add(
            Deduction(
                transaction_id=tx.id,
                deduction_type=d_in.deduction_type,
                label=d_in.label,
                amount_inr=d_in.amount_inr,
                percentage_of_gross=pct,
                reason=d_in.reason,
                supporting_doc_ref=d_in.supporting_doc_ref,
                created_at=created_at,
            )
        )
    db.add(
        ValuationResult(
            transaction_id=tx.id,
            pure_gold_weight_g=valuation.pure_gold_weight_g,
            gross_reference_value_inr=valuation.gross_reference_value_inr,
            total_deductions_inr=valuation.total_deductions_inr,
            calculated_net_value_inr=valuation.calculated_net_value_inr,
            jeweller_offered_value_inr=valuation.jeweller_offered_value_inr,
            offer_difference_inr=valuation.offer_difference_inr,
            offer_difference_explanation=offer_diff_explanation,
            assumptions_json=valuation.assumptions,
            calculation_steps_json=valuation.calculation_steps,
            computed_at=created_at,
        )
    )
    for flag in intel.flags:
        db.add(
            AnomalyFlag(
                transaction_id=tx.id,
                detection_method=flag.detection_method,
                code=flag.code,
                severity=flag.severity,
                title=flag.title,
                message=flag.message,
                evidence_json=flag.evidence,
                created_at=created_at,
            )
        )
    db.add(
        ConsentRecord(
            transaction_id=tx.id,
            customer_profile_id=customer_profile.id,
            consent_type="transaction_recording",
            consent_granted=True,
            consent_text_version="v1.0-en-ta",
            captured_at=created_at,
            captured_by_user_id=jeweller_user.id,
        )
    )
    db.flush()

    record_audit_event(
        db=db,
        action="TRANSACTION_CREATED",
        actor_user=jeweller_user,
        transaction_id=tx.id,
        jeweller_id=jeweller.id,
        details={"transaction_code": tx.transaction_code, "is_demo": True},
        created_at=created_at,
    )

    if jeweller_ack:
        db.add(
            Acknowledgement(
                transaction_id=tx.id,
                party_role="jeweller",
                acknowledged_by_user_id=jeweller_user.id,
                acknowledged_by_name=jeweller_user.full_name,
                acknowledged_at=created_at + timedelta(minutes=2),
                method="in_app_confirmation",
            )
        )
    if customer_ack and customer_user:
        db.add(
            Acknowledgement(
                transaction_id=tx.id,
                party_role="customer",
                acknowledged_by_user_id=customer_user.id,
                acknowledged_by_name=customer_user.full_name,
                acknowledged_at=created_at + timedelta(minutes=4),
                method="customer_portal_confirmation",
            )
        )
    db.flush()
    db.refresh(tx)

    if issue_passport:
        issue_digital_passport(
            db=db,
            tx=tx,
            actor_user=jeweller_user,
            require_jeweller_ack=True,
            signed_at=created_at + timedelta(minutes=5),
        )
    return tx


def seed_demo_data(db: Session) -> None:
    """Seed deterministic, clearly labelled [DEMO] users, shops, and showcase transactions."""
    if db.query(User).filter(User.email == "meena@kaverigold.demo").first() is not None:
        return

    now = datetime.now(timezone.utc).replace(microsecond=0)
    pw_hash = hash_password(DEMO_PASSWORD)

    u_jeweller1 = User(
        email="meena@kaverigold.demo",
        phone="+919842201100",
        full_name="Meena Sundaresan",
        password_hash=pw_hash,
        role="jeweller",
        preferred_language="en",
        is_demo=True,
    )
    u_jeweller2 = User(
        email="arun@maduraigold.demo",
        phone="+919843302200",
        full_name="Arun Pandian",
        password_hash=pw_hash,
        role="jeweller",
        preferred_language="en",
        is_demo=True,
    )
    u_customer = User(
        email="lakshmi@customer.demo",
        phone="+919840122334",
        full_name="Lakshmi Narayanan",
        password_hash=pw_hash,
        role="customer",
        preferred_language="ta",
        is_demo=True,
    )
    u_admin = User(
        email="admin@goldproof.demo",
        phone="+919840099999",
        full_name="GoldProof Platform Admin",
        password_hash=pw_hash,
        role="admin",
        preferred_language="en",
        is_demo=True,
    )
    db.add_all([u_jeweller1, u_jeweller2, u_customer, u_admin])
    db.flush()

    j_kaveri = JewellerProfile(
        user_id=u_jeweller1.id,
        shop_name="Kaveri Heritage Jewellers [DEMO]",
        shop_code="GP-SHOP-KOVAI-01",
        city="Coimbatore",
        state="Tamil Nadu",
        gstin="33AABCK1234F1Z5",
        bis_hallmark_license="BIS-TN-CBE-8821",
        policy_max_deduction_pct=Decimal("5.00"),
        policy_max_wastage_pct=Decimal("3.00"),
        policy_max_fixed_deduction_inr=Decimal("5000.00"),
        policy_notes="Standard old-gold exchange policy: melting & assay deductions capped at 5% or ₹5,000 with itemized customer receipt.",
        valuation_conventions={
            "valuation_basis": "24K pure gold equivalent (net_weight × purity / 100 × 24K_rate)",
            "deductions_itemized": True,
            "maximum_unexplained_deduction_inr": 0,
        },
    )
    j_madurai = JewellerProfile(
        user_id=u_jeweller2.id,
        shop_name="Madurai Bullion & Crafts [DEMO]",
        shop_code="GP-SHOP-MDU-02",
        city="Madurai",
        state="Tamil Nadu",
        gstin="33AABCM9876E1Z2",
        bis_hallmark_license="BIS-TN-MDU-4410",
        policy_max_deduction_pct=Decimal("4.50"),
        policy_max_wastage_pct=Decimal("2.50"),
        policy_max_fixed_deduction_inr=Decimal("4000.00"),
        policy_notes="Transparent net-weight valuation after ultrasonic stone removal.",
        valuation_conventions={
            "valuation_basis": "24K pure gold equivalent",
            "deductions_itemized": True,
        },
    )
    db.add_all([j_kaveri, j_madurai])
    db.flush()

    cp_lakshmi = CustomerProfile(
        user_id=u_customer.id,
        jeweller_id=j_kaveri.id,
        full_name="Lakshmi Narayanan",
        mobile_number="+919840122334",
        preferred_language="ta",
    )
    cp_karthik = CustomerProfile(
        user_id=None,
        jeweller_id=j_kaveri.id,
        full_name="Karthik Sundaram (Walk-in)",
        mobile_number="+919894411223",
        preferred_language="ta",
    )
    cp_madurai = CustomerProfile(
        user_id=None,
        jeweller_id=j_madurai.id,
        full_name="Selvi Muthu (Madurai Walk-in)",
        mobile_number="+919442255667",
        preferred_language="ta",
    )
    db.add_all([cp_lakshmi, cp_karthik, cp_madurai])
    db.flush()

    # 1. GP-DEMO-2026-001: Exact Section 15 canonical showcase (20g, 91.6%, ₹7,600, ₹3,000 deduction = ₹1,36,232)
    _create_demo_transaction(
        db,
        code="GP-DEMO-2026-001",
        jeweller=j_kaveri,
        jeweller_user=u_jeweller1,
        customer_profile=cp_lakshmi,
        customer_user=u_customer,
        item_desc="22K Traditional Gold Haram Necklace [DEMO]",
        category="necklace",
        hallmark_huid="HUID-DEMO01",
        stone_desc="None (pure metal ornament)",
        gross_w=Decimal("20.0000"),
        non_gold_w=Decimal("0.0000"),
        net_w=Decimal("20.0000"),
        purity_pct=Decimal("91.60"),
        karat_label="22K (916)",
        measurement_source="simulated_demo",
        instrument_name="Simulated XRF Benchtop Demo",
        test_report_ref="DEMO-XRF-001",
        rate_24k=Decimal("7600.00"),
        rate_source="Illustrative 24K Bullion Reference [DEMO]",
        deduction_inputs=[
            DeductionInput(
                deduction_type="melting_refining",
                label="Melting & Refining Charge",
                amount_inr=Decimal("2500.00"),
                reason="Standard crucible melting & 24K refining charge (1.80% of gross value) per shop policy.",
                supporting_doc_ref="POL-REF-2026",
            ),
            DeductionInput(
                deduction_type="assay_testing",
                label="XRF Purity Assay Fee",
                amount_inr=Decimal("500.00"),
                reason="Non-destructive XRF purity testing and certificate documentation fee.",
                supporting_doc_ref="DEMO-XRF-001",
            ),
        ],
        offered_value=Decimal("136232.00"),
        offer_diff_explanation=None,
        created_at=now - timedelta(days=2),
        jeweller_ack=True,
        customer_ack=True,
        issue_passport=True,
        notes="[DEMO] Canonical Section 15 reference transaction with full documentation and signed passport.",
    )

    # 2. GP-DEMO-2026-002: Unexplained deduction + policy breach + offer mismatch (triggers Deduction Intelligence)
    _create_demo_transaction(
        db,
        code="GP-DEMO-2026-002",
        jeweller=j_kaveri,
        jeweller_user=u_jeweller1,
        customer_profile=cp_lakshmi,
        customer_user=u_customer,
        item_desc="22K Antique Gold Bangle Pair [DEMO]",
        category="bangle",
        hallmark_huid=None,
        stone_desc="Lac and minor clasp solder",
        gross_w=Decimal("15.5000"),
        non_gold_w=Decimal("0.5000"),
        net_w=Decimal("15.0000"),
        purity_pct=Decimal("91.60"),
        karat_label="22K (916)",
        measurement_source="manual",
        instrument_name="",
        test_report_ref="",
        rate_24k=Decimal("7600.00"),
        rate_source="Illustrative 24K Bullion Reference [DEMO]",
        deduction_inputs=[
            DeductionInput(
                deduction_type="wastage_adjustment",
                label="Unexplained Wastage & Handling Deduction",
                amount_inr=Decimal("6500.00"),
                reason="",
                supporting_doc_ref=None,
            )
        ],
        offered_value=Decimal("96000.00"),
        offer_diff_explanation="",
        created_at=now - timedelta(days=1),
        jeweller_ack=False,
        customer_ack=False,
        issue_passport=False,
        notes="[DEMO] Transaction with unexplained ₹6,500 deduction and manual entry triggering review warnings.",
    )

    # 3. GP-DEMO-2026-003: Pending Customer Acknowledgement (ready for live Tamil Q&A + Ack + Passport issuance)
    _create_demo_transaction(
        db,
        code="GP-DEMO-2026-003",
        jeweller=j_kaveri,
        jeweller_user=u_jeweller1,
        customer_profile=cp_lakshmi,
        customer_user=u_customer,
        item_desc="18K Stone-Studded Gold Ring Set [DEMO]",
        category="ring",
        hallmark_huid="HUID-DEMO03",
        stone_desc="Synthetic ruby & white zircon stones (1.20 g removed prior to weighing)",
        gross_w=Decimal("8.2000"),
        non_gold_w=Decimal("1.2000"),
        net_w=Decimal("7.0000"),
        purity_pct=Decimal("75.00"),
        karat_label="18K (750)",
        measurement_source="simulated_demo",
        instrument_name="Simulated XRF Benchtop Demo",
        test_report_ref="DEMO-XRF-003",
        rate_24k=Decimal("7600.00"),
        rate_source="Illustrative 24K Bullion Reference [DEMO]",
        deduction_inputs=[
            DeductionInput(
                deduction_type="stone_removal",
                label="Stone Unsetting & Ultrasonic Cleaning",
                amount_inr=Decimal("1200.00"),
                reason="Careful stone extraction and ultrasonic cleaning prior to net gold assay.",
                supporting_doc_ref="DEMO-XRF-003",
            )
        ],
        offered_value=Decimal("38700.00"),
        offer_diff_explanation=None,
        created_at=now - timedelta(hours=4),
        jeweller_ack=True,
        customer_ack=False,
        issue_passport=False,
        notes="[DEMO] Ready for customer review, Tamil AI voice Q&A, customer acknowledgement, and passport signing.",
    )

    # 4. GP-DEMO-2026-004: Walk-in signed transaction for Kaveri trend history
    _create_demo_transaction(
        db,
        code="GP-DEMO-2026-004",
        jeweller=j_kaveri,
        jeweller_user=u_jeweller1,
        customer_profile=cp_karthik,
        customer_user=None,
        item_desc="24K Mint Gold Coin (10 g) [DEMO]",
        category="coin",
        hallmark_huid=None,
        stone_desc="Sealed blister pack opened in customer presence",
        gross_w=Decimal("10.0000"),
        non_gold_w=Decimal("0.0000"),
        net_w=Decimal("10.0000"),
        purity_pct=Decimal("99.50"),
        karat_label="24K (995)",
        measurement_source="simulated_demo",
        instrument_name="Simulated XRF Benchtop Demo",
        test_report_ref="DEMO-XRF-004",
        rate_24k=Decimal("7600.00"),
        rate_source="Illustrative 24K Bullion Reference [DEMO]",
        deduction_inputs=[
            DeductionInput(
                deduction_type="assay_testing",
                label="Coin Purity Verification Fee",
                amount_inr=Decimal("400.00"),
                reason="Standard 24K coin ultrasonic and conductivity verification fee.",
                supporting_doc_ref="DEMO-XRF-004",
            )
        ],
        offered_value=Decimal("75220.00"),
        offer_diff_explanation=None,
        created_at=now - timedelta(days=5),
        jeweller_ack=True,
        customer_ack=False,
        issue_passport=True,
        notes="[DEMO] Walk-in 24K coin exchange with signed passport.",
    )

    # 5. GP-DEMO-2026-005: Tenant-isolated transaction belonging strictly to Jeweller 2 (Madurai)
    _create_demo_transaction(
        db,
        code="GP-DEMO-2026-005",
        jeweller=j_madurai,
        jeweller_user=u_jeweller2,
        customer_profile=cp_madurai,
        customer_user=None,
        item_desc="22K Madurai Rope Chain [DEMO]",
        category="chain",
        hallmark_huid="HUID-MDU05",
        stone_desc="None",
        gross_w=Decimal("12.0000"),
        non_gold_w=Decimal("0.0000"),
        net_w=Decimal("12.0000"),
        purity_pct=Decimal("91.60"),
        karat_label="22K (916)",
        measurement_source="simulated_demo",
        instrument_name="Simulated XRF Demo - Madurai",
        test_report_ref="DEMO-MDU-005",
        rate_24k=Decimal("7590.00"),
        rate_source="Madurai Bullion Reference [DEMO]",
        deduction_inputs=[
            DeductionInput(
                deduction_type="melting_refining",
                label="Refining Charge",
                amount_inr=Decimal("1500.00"),
                reason="Standard chain melting and solder refining charge.",
                supporting_doc_ref="DEMO-MDU-005",
            )
        ],
        offered_value=Decimal("81929.28"),
        offer_diff_explanation=None,
        created_at=now - timedelta(days=1),
        jeweller_ack=True,
        customer_ack=False,
        issue_passport=True,
        notes="[DEMO] Tenant-isolated transaction belonging to Madurai Bullion & Crafts.",
    )

    db.commit()
