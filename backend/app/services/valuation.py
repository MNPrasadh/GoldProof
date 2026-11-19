"""Transparent Decimal valuation engine for gold exchange transactions."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Optional

Q_WEIGHT = Decimal("0.0001")
Q_MONEY = Decimal("0.01")
Q_PCT = Decimal("0.01")


def q_weight(val: Decimal) -> Decimal:
    return val.quantize(Q_WEIGHT, rounding=ROUND_HALF_UP)


def q_money(val: Decimal) -> Decimal:
    return val.quantize(Q_MONEY, rounding=ROUND_HALF_UP)


def q_pct(val: Decimal) -> Decimal:
    return val.quantize(Q_PCT, rounding=ROUND_HALF_UP)


@dataclass
class DeductionInput:
    deduction_type: str
    label: str
    amount_inr: Decimal
    reason: Optional[str] = None
    supporting_doc_ref: Optional[str] = None


@dataclass
class ValuationOutput:
    gross_weight_g: Decimal
    non_gold_weight_g: Decimal
    net_gold_weight_g: Decimal
    purity_pct: Decimal
    pure_gold_weight_g: Decimal
    rate_24k_per_g: Decimal
    gross_reference_value_inr: Decimal
    total_deductions_inr: Decimal
    calculated_net_value_inr: Decimal
    jeweller_offered_value_inr: Decimal
    offer_difference_inr: Decimal
    deduction_percentages: list[Decimal]
    assumptions: dict[str, Any]
    calculation_steps: list[dict[str, Any]]


def calculate_valuation(
    gross_weight_g: Decimal,
    non_gold_weight_g: Decimal,
    net_gold_weight_g: Optional[Decimal],
    purity_pct: Decimal,
    rate_24k_per_g: Decimal,
    deductions: Iterable[DeductionInput],
    jeweller_offered_value_inr: Optional[Decimal] = None,
    offer_difference_explanation: Optional[str] = None,
    measurement_source: str = "manual",
    rate_source: str = "shop_board",
    shop_conventions: Optional[dict[str, Any]] = None,
) -> ValuationOutput:
    """Compute transparent, step-by-step gold exchange valuation using exact Decimal arithmetic."""
    gross_w = q_weight(Decimal(gross_weight_g))
    non_gold_w = q_weight(Decimal(non_gold_weight_g))
    derived_net_w = q_weight(gross_w - non_gold_w)
    effective_net_w = q_weight(Decimal(net_gold_weight_g)) if net_gold_weight_g is not None else derived_net_w

    purity = q_pct(Decimal(purity_pct))
    rate = q_money(Decimal(rate_24k_per_g))

    pure_gold_w = q_weight(effective_net_w * purity / Decimal("100"))
    gross_ref_val = q_money(pure_gold_w * rate)

    deduction_list = list(deductions)
    total_ded = q_money(sum((q_money(Decimal(d.amount_inr)) for d in deduction_list), Decimal("0.00")))

    deduction_pcts: list[Decimal] = []
    for d in deduction_list:
        amt = q_money(Decimal(d.amount_inr))
        pct = q_pct((amt / gross_ref_val) * Decimal("100")) if gross_ref_val > Decimal("0.00") else Decimal("0.00")
        deduction_pcts.append(pct)

    calc_net_val = q_money(gross_ref_val - total_ded)
    offered_val = q_money(Decimal(jeweller_offered_value_inr)) if jeweller_offered_value_inr is not None else calc_net_val
    offer_diff = q_money(offered_val - calc_net_val)

    steps = [
        {
            "step": 1,
            "code": "NET_GOLD_WEIGHT",
            "label": "Net gold-bearing weight",
            "formula": f"{gross_w} g (gross) - {non_gold_w} g (non-gold) = {effective_net_w} g",
            "value": format(effective_net_w, "f"),
            "unit": "g",
        },
        {
            "step": 2,
            "code": "PURE_GOLD_EQUIVALENT",
            "label": "24K pure gold equivalent",
            "formula": f"{effective_net_w} g × {purity}% / 100 = {pure_gold_w} g",
            "value": format(pure_gold_w, "f"),
            "unit": "g",
        },
        {
            "step": 3,
            "code": "GROSS_REFERENCE_VALUE",
            "label": "Gross reference value at 24K rate",
            "formula": f"{pure_gold_w} g × ₹{rate}/g = ₹{gross_ref_val}",
            "value": format(gross_ref_val, "f"),
            "unit": "INR",
        },
        {
            "step": 4,
            "code": "DOCUMENTED_DEDUCTIONS",
            "label": "Total itemized deductions",
            "formula": " + ".join([f"{d.label}: ₹{q_money(Decimal(d.amount_inr))}" for d in deduction_list]) or "₹0.00",
            "value": format(total_ded, "f"),
            "unit": "INR",
        },
        {
            "step": 5,
            "code": "CALCULATED_NET_VALUE",
            "label": "Calculated net exchange value",
            "formula": f"₹{gross_ref_val} - ₹{total_ded} = ₹{calc_net_val}",
            "value": format(calc_net_val, "f"),
            "unit": "INR",
        },
        {
            "step": 6,
            "code": "FINAL_OFFER_COMPARISON",
            "label": "Jeweller offered value vs calculated value",
            "formula": f"Offered ₹{offered_val} (Difference: ₹{offer_diff})",
            "value": format(offered_val, "f"),
            "unit": "INR",
        },
    ]

    assumptions = {
        "formula_basis": "net_gold_weight × (purity_pct / 100) × rate_24k_per_g - itemized_deductions",
        "rounding_rule": "HALF_UP (4 decimals for grams, 2 decimals for INR)",
        "measurement_source": measurement_source,
        "rate_source": rate_source,
        "offer_difference_explained": bool(offer_difference_explanation and offer_difference_explanation.strip()),
        "shop_conventions": shop_conventions or {
            "valuation_basis": "24K pure gold equivalent",
            "deductions_itemized": True,
            "wastage_policy_note": "Deductions must be explicitly documented with customer visibility",
        },
    }

    return ValuationOutput(
        gross_weight_g=gross_w,
        non_gold_weight_g=non_gold_w,
        net_gold_weight_g=effective_net_w,
        purity_pct=purity,
        pure_gold_weight_g=pure_gold_w,
        rate_24k_per_g=rate,
        gross_reference_value_inr=gross_ref_val,
        total_deductions_inr=total_ded,
        calculated_net_value_inr=calc_net_val,
        jeweller_offered_value_inr=offered_val,
        offer_difference_inr=offer_diff,
        deduction_percentages=deduction_pcts,
        assumptions=assumptions,
        calculation_steps=steps,
    )
