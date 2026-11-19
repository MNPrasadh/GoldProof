"""Evidence-grounded Tamil & English AI assistant for explaining gold exchange transactions."""

import re
from decimal import Decimal
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.models.entities import Transaction


def format_inr(amount: Decimal | str | float) -> str:
    """Format an INR amount using Indian numbering commas (e.g. 1,36,232.00)."""
    dec = Decimal(str(amount)).quantize(Decimal("0.01"))
    sign = "-" if dec < 0 else ""
    abs_str = f"{abs(dec):.2f}"
    whole, frac = abs_str.split(".")
    if len(whole) <= 3:
        formatted = whole
    else:
        last3 = whole[-3:]
        rest = whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted = ",".join(groups) + "," + last3
    return f"{sign}₹{formatted}.{frac}"


def detect_language(question: str, requested_language: Optional[str] = None) -> str:
    """Detect whether to respond in Tamil ('ta') or English ('en')."""
    if requested_language in ("ta", "en"):
        # If the user explicitly asks in Tamil script while UI was 'en', prefer Tamil
        if re.search(r"[\u0B80-\u0BFF]", question):
            return "ta"
        return requested_language
    if re.search(r"[\u0B80-\u0BFF]", question):
        return "ta"
    tanglish_markers = ("evvalavu", "mathippu", "thangam", "kazhivu", "yen", "enna")
    lower = question.lower()
    if any(tok in lower for tok in tanglish_markers):
        return "ta"
    return "en"


def build_transaction_evidence_context(tx: Transaction) -> dict[str, Any]:
    """Assemble strict factual evidence dictionary from persisted transaction rows."""
    m = tx.measurement_record
    r = tx.rate_record
    v = tx.valuation_result
    missing_items: list[str] = []

    if m is None:
        missing_items.append("Weight and purity measurement record")
    else:
        if m.measurement_source == "manual" or not m.test_report_ref:
            missing_items.append("Assay instrument report reference (measurement was entered manually or lacks test report ID)")
        if m.measurement_source == "simulated_demo":
            missing_items.append("Live hardware reading (labelled as simulated demo measurement)")

    unexplained_deductions = [
        d.label for d in tx.deductions if d.amount_inr > 0 and (not d.reason or len(d.reason.strip()) < 8)
    ]
    if unexplained_deductions:
        missing_items.append(f"Written reason for deduction(s): {', '.join(unexplained_deductions)}")

    if v and abs(v.offer_difference_inr) > Decimal("50") and not (
        v.offer_difference_explanation and v.offer_difference_explanation.strip()
    ):
        missing_items.append("Explanation for difference between calculated value and jeweller offer")

    return {
        "transaction_code": tx.transaction_code,
        "status": tx.status,
        "is_demo": bool(tx.is_demo),
        "shop_name": tx.jeweller.shop_name if tx.jeweller else "Unknown Shop",
        "items": [i.item_description for i in tx.jewellery_items],
        "gross_weight_g": str(m.gross_weight_g) if m else None,
        "non_gold_weight_g": str(m.non_gold_weight_g) if m else None,
        "net_gold_weight_g": str(m.net_gold_weight_g) if m else None,
        "purity_pct": str(m.purity_pct) if m else None,
        "purity_karat_label": m.purity_karat_label if m else None,
        "measurement_source": m.measurement_source if m else None,
        "instrument_name": m.instrument_name if m else None,
        "test_report_ref": m.test_report_ref if m else None,
        "rate_24k_per_g": str(r.rate_24k_per_g) if r else None,
        "rate_source": r.rate_source if r else None,
        "pure_gold_weight_g": str(v.pure_gold_weight_g) if v else None,
        "gross_reference_value_inr": str(v.gross_reference_value_inr) if v else None,
        "total_deductions_inr": str(v.total_deductions_inr) if v else None,
        "calculated_net_value_inr": str(v.calculated_net_value_inr) if v else None,
        "jeweller_offered_value_inr": str(v.jeweller_offered_value_inr) if v else None,
        "offer_difference_inr": str(v.offer_difference_inr) if v else None,
        "offer_difference_explanation": v.offer_difference_explanation if v else None,
        "deductions": [
            {
                "label": d.label,
                "type": d.deduction_type,
                "amount_inr": str(d.amount_inr),
                "reason": d.reason or "",
            }
            for d in tx.deductions
        ],
        "flags": [
            {"method": f.detection_method, "severity": f.severity, "title": f.title, "message": f.message}
            for f in tx.anomaly_flags
        ],
        "missing_information": missing_items,
        "has_digital_passport": tx.digital_passport is not None,
    }


def _local_evidence_answer(tx: Transaction, question: str, lang: str) -> tuple[str, list[str]]:
    """Deterministic, evidence-grounded bilingual explainer for Tamil & English."""
    ctx = build_transaction_evidence_context(tx)
    q = question.lower()
    citations = [f"Transaction {ctx['transaction_code']}"]

    if tx.measurement_record is None or tx.rate_record is None or tx.valuation_result is None:
        if lang == "ta":
            return (
                f"பரிவர்த்தனை {ctx['transaction_code']} இல் முழுமையான எடை, தூய்மை அல்லது விலை விவரங்கள் இன்னும் பதிவு செய்யப்படவில்லை.",
                citations,
            )
        return (
            f"Transaction {ctx['transaction_code']} is missing weight, purity, or gold rate evidence. "
            "No value can be calculated until those measurements are recorded.",
            citations,
        )

    gross_w = ctx["gross_weight_g"]
    non_gold_w = ctx["non_gold_weight_g"]
    net_w = ctx["net_gold_weight_g"]
    purity = ctx["purity_pct"]
    karat = ctx["purity_karat_label"]
    pure_w = ctx["pure_gold_weight_g"]
    rate = format_inr(ctx["rate_24k_per_g"])
    gross_val = format_inr(ctx["gross_reference_value_inr"])
    tot_ded = format_inr(ctx["total_deductions_inr"])
    net_val = format_inr(ctx["calculated_net_value_inr"])
    offered_val = format_inr(ctx["jeweller_offered_value_inr"])
    offer_diff = Decimal(ctx["offer_difference_inr"])

    citations.extend([
        f"Net weight: {net_w} g",
        f"Purity: {purity}% ({karat})",
        f"24K Rate: {rate}/g",
        f"Calculated Net Value: {net_val}",
    ])

    wants_deduction = any(
        k in q for k in ("deduct", "3000", "3,000", "cut", "less", "charge", "கழி", "பிடித்தம்", "கட்டணம்", "kazhivu")
    )
    wants_purity = any(k in q for k in ("purity", "22k", "91.6", "karat", "carat", "தூய்மை", "கேரட்", "மாற்று"))
    wants_warning = any(
        k in q for k in ("warning", "flag", "review", "missing", "issue", "problem", "அறிவிப்பு", "குறை", "சரிபார்ப்பு")
    )
    wants_passport = any(k in q for k in ("passport", "sign", "qr", "hash", "verify", "பாஸ்போர்ட்", "கையொப்பம்"))

    if lang == "ta":
        parts: list[str] = []
        if wants_purity and not wants_deduction:
            parts.append(
                f"உங்கள் நகை ({', '.join(ctx['items']) or 'Gold item'}) {purity}% ({karat}) தூய்மையுடன் பதிவு செய்யப்பட்டுள்ளது. "
                f"அதாவது {net_w} கிராம் நிகர எடையில் {pure_w} கிராம் 24K சுத்தத் தங்கம் உள்ளது."
            )
            if karat and "22" in karat:
                parts.append("22K (91.6%) என்பது 100 கிராம் உலோகத்தில் 91.6 கிராம் சுத்தத் தங்கம் உள்ளதைக் குறிக்கும்.")
        elif wants_deduction:
            parts.append(f"பரிவர்த்தனை {ctx['transaction_code']} இல் மொத்த கழிவு: {tot_ded}.")
            if ctx["deductions"]:
                for d in ctx["deductions"]:
                    reason_txt = d["reason"] if d["reason"] else "காரணம் பதிவு செய்யப்படவில்லை (விளக்கம் தேவை)"
                    parts.append(f"• {d['label']}: {format_inr(d['amount_inr'])} — {reason_txt}")
            else:
                parts.append("எந்தக் கழிவும் பதிவு செய்யப்படவில்லை.")
            parts.append(f"மொத்த தங்க மதிப்பு {gross_val} - கழிவு {tot_ded} = கணக்கிடப்பட்ட மதிப்பு {net_val}.")
        elif wants_warning:
            if ctx["flags"]:
                parts.append("இந்தப் பரிவர்த்தனையில் காணப்பட்ட முக்கிய குறிப்புகள்:")
                for f in ctx["flags"]:
                    parts.append(f"• [{f['severity']}] {f['message']}")
            else:
                parts.append("இந்தப் பரிவர்த்தனையில் கழிவு விதிமுறை எச்சரிக்கைகள் எதுவும் இல்லை.")
        elif wants_passport:
            if ctx["has_digital_passport"]:
                parts.append(
                    "இந்தப் பரிவர்த்தனைக்கு Ed25519 டிஜிட்டல் கையொப்பமிட்ட Digital Gold Passport உருவாக்கப்பட்டுள்ளது. "
                    "கையொப்பத்திற்குப் பிறகு பதிவு மாற்றப்படவில்லை என்பதை QR குறியீடு உறுதி செய்கிறது."
                )
            else:
                parts.append("இந்தப் பரிவர்த்தனைக்கு இன்னும் Digital Gold Passport கையொப்பமிடப்படவில்லை.")
        else:
            # General valuation / value question ("எனது தங்கத்தின் மதிப்பு எவ்வளவு?")
            parts.append(
                f"பரிவர்த்தனை {ctx['transaction_code']} கணக்கீடு (படிப்படியாக):"
            )
            parts.append(
                f"1) எடை: மொத்த எடை {gross_w} g - தங்கமற்ற எடை {non_gold_w} g = நிகர தங்க எடை {net_w} g."
            )
            parts.append(
                f"2) சுத்தத் தங்கம்: {net_w} g × {purity}% ({karat}) = {pure_w} g 24K சுத்தத் தங்கம்."
            )
            parts.append(
                f"3) மொத்த மதிப்பு: {pure_w} g × {rate}/g ({ctx['rate_source']}) = {gross_val}."
            )
            if ctx["deductions"]:
                ded_lines = "; ".join(
                    f"{d['label']} {format_inr(d['amount_inr'])} ({d['reason'] or 'காரணம் இல்லை'})"
                    for d in ctx["deductions"]
                )
                parts.append(f"4) கழிவுகள் ({tot_ded}): {ded_lines}.")
            else:
                parts.append("4) கழிவுகள்: ₹0.00.")
            parts.append(f"5) இறுதி கணக்கிடப்பட்ட மதிப்பு: {net_val}. நகைக்கடை வழங்கும் விலை: {offered_val}.")

        if abs(offer_diff) > Decimal("0.01"):
            exp = ctx["offer_difference_explanation"] or "வித்தியாசத்திற்கான காரணம் பதிவு செய்யப்படவில்லை"
            parts.append(f"குறிப்பு: கணக்கிடப்பட்ட மதிப்பிற்கும் வழங்கப்பட்ட விலைக்கும் {format_inr(offer_diff)} வித்தியாசம் உள்ளது ({exp}).")

        if ctx["missing_information"]:
            parts.append("தகவல் வெளிப்படைத்தன்மை குறிப்பு (குறைபாடுகள்/சரிபார்க்க வேண்டியவை):")
            for miss in ctx["missing_information"]:
                parts.append(f"• {miss}")

        if ctx["measurement_source"] == "simulated_demo":
            parts.append("கவனிக்கவும்: இது செயல்விளக்க (Demo) அளவீட்டுத் தரவு ஆகும்.")

        return "\n".join(parts), citations

    # English response
    parts = []
    if wants_purity and not wants_deduction:
        parts.append(
            f"Your item ({', '.join(ctx['items']) or 'Gold ornament'}) is recorded at {purity}% purity ({karat}). "
            f"That means {net_w} g of net gold-bearing weight equals {pure_w} g of 24K pure gold equivalent "
            f"({net_w} × {purity} / 100 = {pure_w} g)."
        )
        if karat and "22" in karat:
            parts.append("22K (typically 91.6% purity) means 91.6 parts out of 100 are pure gold, with 8.4 parts alloy.")
    elif wants_deduction:
        parts.append(f"Total documented deductions for {ctx['transaction_code']}: {tot_ded}.")
        if ctx["deductions"]:
            for d in ctx["deductions"]:
                reason = d["reason"] if d["reason"] else "MISSING EXPLANATION — no written reason recorded"
                parts.append(f"• {d['label']} ({d['type']}): {format_inr(d['amount_inr'])} — {reason}")
        else:
            parts.append("• No deductions were recorded.")
        parts.append(f"Calculation: Gross reference value {gross_val} - {tot_ded} = {net_val}.")
    elif wants_warning:
        if ctx["flags"]:
            parts.append(f"GoldProof recorded {len(ctx['flags'])} review/informational notice(s):")
            for f in ctx["flags"]:
                parts.append(f"• [{f['method']} | {f['severity']}] {f['message']}")
        else:
            parts.append("No rule-based or anomaly warnings are flagged on this transaction.")
    elif wants_passport:
        if ctx["has_digital_passport"]:
            parts.append(
                "A cryptographically signed Digital Gold Passport (Ed25519 + SHA-256) has been issued. "
                "Scanning its QR code verifies that the signed record has not changed since signing, though it "
                "does not independently prove manual measurements."
            )
        else:
            parts.append("A Digital Gold Passport has not been signed for this transaction yet.")
    else:
        parts.append(f"Step-by-step valuation for {ctx['transaction_code']}:")
        parts.append(f"1. Net gold weight: {gross_w} g gross - {non_gold_w} g non-gold = {net_w} g.")
        parts.append(f"2. Pure gold equivalent: {net_w} g × {purity}% ({karat}) = {pure_w} g (24K equivalent).")
        parts.append(f"3. Gross reference value: {pure_w} g × {rate}/g ({ctx['rate_source']}) = {gross_val}.")
        if ctx["deductions"]:
            ded_summary = "; ".join(
                f"{d['label']}: {format_inr(d['amount_inr'])} ({d['reason'] or 'No reason documented'})"
                for d in ctx["deductions"]
            )
            parts.append(f"4. Itemized deductions ({tot_ded}): {ded_summary}.")
        else:
            parts.append("4. Itemized deductions: ₹0.00.")
        parts.append(f"5. Calculated net value: {net_val}. Jeweller offered value: {offered_val}.")

    if abs(offer_diff) > Decimal("0.01"):
        exp = ctx["offer_difference_explanation"] or "No written explanation provided for offer difference"
        parts.append(f"Offer variance: {format_inr(offer_diff)} ({exp}).")

    if ctx["missing_information"]:
        parts.append("Missing or incomplete evidence noted:")
        for miss in ctx["missing_information"]:
            parts.append(f"• {miss}")

    if ctx["measurement_source"] == "simulated_demo":
        parts.append("Note: This record uses simulated demo measurement values for demonstration.")

    return "\n".join(parts), citations


async def answer_transaction_question(
    tx: Transaction,
    question: str,
    requested_language: Optional[str] = None,
) -> dict[str, Any]:
    """Answer a customer or jeweller question grounded strictly in transaction evidence."""
    settings = get_settings()
    lang = detect_language(question, requested_language)
    evidence_ctx = build_transaction_evidence_context(tx)

    if settings.LLM_API_KEY.strip() and settings.LLM_PROVIDER.lower() not in ("", "local", "local_evidence_explainer"):
        system_prompt = (
            "You are GoldProof, a neutral, transparent gold-exchange explainer. "
            "Use ONLY the JSON evidence provided. Never invent purity percentages, rates, weights, or deductions. "
            "State clearly if any explanation or instrument evidence is missing. Never accuse anyone of fraud. "
            f"Respond clearly in {'Tamil (தமிழ்)' if lang == 'ta' else 'English'}."
        )
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.LLM_API_KEY.strip()}"},
                    json={
                        "model": settings.LLM_MODEL,
                        "temperature": 0.1,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": f"Transaction Evidence:\n{evidence_ctx}\n\nQuestion: {question}",
                            },
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                answer_text = data["choices"][0]["message"]["content"].strip()
                return {
                    "transaction_id": tx.id,
                    "transaction_code": tx.transaction_code,
                    "language": lang,
                    "answer": answer_text,
                    "citations": [f"Transaction {tx.transaction_code}"],
                    "missing_information": evidence_ctx["missing_information"],
                    "provider_mode": f"external_llm:{settings.LLM_PROVIDER}",
                    "is_external_llm": True,
                }
        except Exception:
            # Honest fallback to local evidence explainer if external LLM fails
            pass

    answer_text, citations = _local_evidence_answer(tx, question, lang)
    return {
        "transaction_id": tx.id,
        "transaction_code": tx.transaction_code,
        "language": lang,
        "answer": answer_text,
        "citations": citations,
        "missing_information": evidence_ctx["missing_information"],
        "provider_mode": "local_evidence_explainer",
        "is_external_llm": False,
    }
