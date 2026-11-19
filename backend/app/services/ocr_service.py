"""OCR extraction service with PaddleOCR adapter and clearly labelled MockOCRAdapter."""

import io
import re
from typing import Any, Protocol

from PIL import Image, UnidentifiedImageError

from app.config import get_settings


class OCRAdapter(Protocol):
    provider_name: str
    is_simulated: bool

    def extract(self, file_bytes: bytes, filename: str, document_type: str) -> dict[str, Any]:
        ...


def _parse_fields_from_text(raw_text: str, document_type: str) -> dict[str, Any]:
    """Extract structured gold measurement and valuation fields from OCR text lines."""
    gross_match = re.search(r"gross(?:\s*wt|\s*weight)?\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?)\s*g", raw_text, re.I)
    net_match = re.search(r"net(?:\s*wt|\s*weight)?\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?)\s*g", raw_text, re.I)
    purity_match = re.search(r"([0-9]{2}(?:\.[0-9]+)?)\s*%", raw_text)
    rate_match = re.search(r"(?:rate|24k)\s*[:=-]?\s*(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", raw_text, re.I)
    ref_match = re.search(r"(?:report|ref|receipt|no\.?)\s*[:=#-]?\s*([A-Z0-9-]{4,})", raw_text, re.I)

    return {
        "document_type": document_type,
        "item_description": "Extracted Gold Ornament" if "ornament" in raw_text.lower() else "Gold Jewellery Item",
        "gross_weight_g": gross_match.group(1) if gross_match else None,
        "non_gold_weight_g": "0.00",
        "net_gold_weight_g": net_match.group(1) if net_match else (gross_match.group(1) if gross_match else None),
        "purity_pct": purity_match.group(1) if purity_match else None,
        "rate_24k_per_g": rate_match.group(1).replace(",", "") if rate_match else None,
        "test_report_ref": ref_match.group(1) if ref_match else None,
    }


class PaddleOCRAdapter:
    """Real PaddleOCR adapter (used only when paddleocr package is installed)."""

    provider_name = "paddleocr"
    is_simulated = False

    def __init__(self) -> None:
        from paddleocr import PaddleOCR  # type: ignore

        self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    def extract(self, file_bytes: bytes, filename: str, document_type: str) -> dict[str, Any]:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        import numpy as np

        result = self._ocr.ocr(np.array(image), cls=True)
        lines: list[str] = []
        confidences: list[float] = []
        for page in result or []:
            for line in page or []:
                text, conf = line[1]
                lines.append(str(text))
                confidences.append(float(conf))

        raw_text = "\n".join(lines)
        avg_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
        fields = _parse_fields_from_text(raw_text, document_type)
        return {
            "provider": self.provider_name,
            "is_simulated": self.is_simulated,
            "requires_human_confirmation": True,
            "confidence": avg_conf,
            "raw_text": raw_text,
            "extracted_fields": fields,
            "warning": "Verify all OCR-extracted values against the physical document before saving.",
        }


class MockOCRAdapter:
    """Clearly labelled mock OCR adapter when PaddleOCR is not installed in the environment."""

    provider_name = "mock_ocr_adapter"
    is_simulated = True

    def extract(self, file_bytes: bytes, filename: str, document_type: str) -> dict[str, Any]:
        # Validate image bytes if image, or allow plain text sample slips
        image_meta = "text_or_document"
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                image_meta = f"{img.format} {img.width}x{img.height}"
        except (UnidentifiedImageError, OSError):
            try:
                decoded = file_bytes.decode("utf-8", errors="ignore").strip()
                if decoded and any(k in decoded.lower() for k in ("gross", "purity", "rate", "weight")):
                    fields = _parse_fields_from_text(decoded, document_type)
                    return {
                        "provider": self.provider_name,
                        "is_simulated": True,
                        "requires_human_confirmation": True,
                        "confidence": 0.78,
                        "raw_text": decoded,
                        "extracted_fields": fields,
                        "warning": (
                            "SIMULATED OCR ADAPTER: PaddleOCR is not installed in this environment. "
                            "These sample/parsed fields MUST be verified and confirmed by a human before saving."
                        ),
                    }
            except Exception:
                pass

        samples = {
            "assay_report": {
                "raw_text": (
                    "SPECTRO XRF ASSAY REPORT #XRF-2026-4412\n"
                    "Item: 22K Gold Bangle Pair\n"
                    "Gross Weight: 18.40 g | Stone Wt: 0.40 g | Net Gold Wt: 18.00 g\n"
                    "Assayed Purity: 91.60 % (22K)"
                ),
                "extracted_fields": {
                    "document_type": document_type,
                    "item_description": "22K Gold Bangle Pair (OCR Draft)",
                    "gross_weight_g": "18.40",
                    "non_gold_weight_g": "0.40",
                    "net_gold_weight_g": "18.00",
                    "purity_pct": "91.60",
                    "rate_24k_per_g": "7600.00",
                    "test_report_ref": "XRF-2026-4412",
                    "instrument_name": "SpectroXRF Analyzer (Confirm on Slip)",
                },
            },
            "handwritten_register": {
                "raw_text": (
                    "LEDGER ENTRY #REG-108 (Handwritten Register)\n"
                    "Customer Ornament: Old Gold Thali Chain\n"
                    "Gross Wt: 24.50 g | Wax/Thread: 0.50 g | Net: 24.00 g\n"
                    "Touch Purity: 88.50 % | Rate: Rs.7600/g"
                ),
                "extracted_fields": {
                    "document_type": document_type,
                    "item_description": "Old Gold Thali Chain (Register OCR Draft)",
                    "gross_weight_g": "24.50",
                    "non_gold_weight_g": "0.50",
                    "net_gold_weight_g": "24.00",
                    "purity_pct": "88.50",
                    "rate_24k_per_g": "7600.00",
                    "test_report_ref": "REG-108",
                    "instrument_name": "",
                },
            },
            "paper_receipt": {
                "raw_text": (
                    "OLD GOLD EXCHANGE SLIP #RCP-902\n"
                    "Item: 22K Necklace | Gross Weight: 20.00 g | Net: 20.00 g\n"
                    "Purity: 91.60 % | 24K Rate: 7600.00 | Deduction: 3000.00"
                ),
                "extracted_fields": {
                    "document_type": document_type,
                    "item_description": "22K Gold Necklace (Receipt OCR Draft)",
                    "gross_weight_g": "20.00",
                    "non_gold_weight_g": "0.00",
                    "net_gold_weight_g": "20.00",
                    "purity_pct": "91.60",
                    "rate_24k_per_g": "7600.00",
                    "test_report_ref": "RCP-902",
                    "instrument_name": "",
                },
            },
        }
        chosen = samples.get(document_type, samples["paper_receipt"])
        return {
            "provider": self.provider_name,
            "is_simulated": True,
            "requires_human_confirmation": True,
            "confidence": 0.74,
            "image_metadata": f"{filename} ({image_meta})",
            "raw_text": chosen["raw_text"],
            "extracted_fields": chosen["extracted_fields"],
            "warning": (
                "SIMULATED OCR ADAPTER: PaddleOCR runtime is unavailable here, so illustrative sample "
                "extraction is returned. Review and confirm every value before saving."
            ),
        }


def run_ocr_extraction(file_bytes: bytes, filename: str, document_type: str) -> dict[str, Any]:
    """Run configured OCR adapter and enforce human-in-the-loop confirmation."""
    provider_pref = get_settings().OCR_PROVIDER.lower()
    if provider_pref in ("auto", "paddleocr"):
        try:
            adapter: OCRAdapter = PaddleOCRAdapter()
            return adapter.extract(file_bytes, filename, document_type)
        except Exception:
            if provider_pref == "paddleocr":
                # Do not fail silently; report simulated fallback clearly
                pass
    return MockOCRAdapter().extract(file_bytes, filename, document_type)
