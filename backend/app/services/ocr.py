import json
import re
import time
from pathlib import Path

import httpx
from docx import Document
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import OcrRecognitionLog


def _extract_amount(text: str) -> str | None:
    match = re.search(r"(\d+(?:,\d{3})*(?:\.\d{1,2})?)", text)
    return match.group(1).replace(",", "") if match else None


def _extract_date(text: str) -> str | None:
    match = re.search(r"(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})", text)
    if not match:
        return None
    return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"


def _extract_contract(text: str) -> dict:
    amount = _extract_amount(text)
    contract_no = re.search(r"(HT[-_A-Za-z0-9]{4,})", text, re.I)
    return {
        "project_name": _match_after(text, ["项目名称", "项目名"]) or "",
        "contract_amount": amount or "",
        "contract_no": contract_no.group(1) if contract_no else "",
        "sign_date": _extract_date(text) or "",
        "party_a": _match_after(text, ["甲方", "客户名称", "客户"]) or "",
    }


def _extract_invoice(text: str) -> dict:
    invoice_no = re.search(r"(?:发票号码|发票号|号码)[:：\s]*([A-Za-z0-9-]{6,30})", text)
    return {
        "invoice_no": invoice_no.group(1) if invoice_no else "",
        "amount": _extract_amount(text) or "",
        "invoice_date": _extract_date(text) or "",
        "buyer": _match_after(text, ["购买方", "购方", "买方"]) or "",
        "seller": _match_after(text, ["销售方", "销方", "卖方"]) or "",
    }


def _match_after(text: str, labels: list[str]) -> str | None:
    for label in labels:
        match = re.search(rf"{label}[:：\s]*([^\n\r，,;；]{{2,80}})", text)
        if match:
            return match.group(1).strip()
    return None


def _confidence_for(info: dict, base: float) -> dict:
    return {key: (base if value else 0.0) for key, value in info.items()}


def _parse_docx(path: Path) -> str:
    document = Document(str(path))
    lines = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            values = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if values:
                lines.append(" ".join(values))
    return "\n".join(lines)


def _read_document_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return _parse_docx(path)
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else path.name


def _call_paddleocr(path: Path, recognition_type: str) -> tuple[str, float, list]:
    settings = get_settings()
    with path.open("rb") as file:
        files = {"file": (path.name, file, "application/octet-stream")}
        response = httpx.post(settings.paddleocr_url, params={"type": recognition_type}, files=files, timeout=60)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data", payload)
    lines = data.get("lines") or data.get("raw_text") or []
    texts: list[str] = []
    confidences: list[float] = []
    for line in lines:
        if isinstance(line, dict):
            texts.append(str(line.get("text") or ""))
            if line.get("confidence") is not None:
                confidences.append(float(line["confidence"]))
        elif isinstance(line, (list, tuple)) and line:
            texts.append(str(line[0]))
            if len(line) >= 3:
                try:
                    confidences.append(float(line[2]))
                except (TypeError, ValueError):
                    pass
        else:
            texts.append(str(line))
    raw_text = "\n".join(t for t in texts if t)
    confidence = sum(confidences) / len(confidences) if confidences else float(data.get("confidence") or 0)
    return raw_text, confidence, lines


def recognize_file(db: Session, file_path: str, recognition_type: str) -> dict:
    start = time.perf_counter()
    path = Path(file_path)
    suffix = path.suffix.lower()
    engine = "parser" if suffix in {".doc", ".docx"} else "paddleocr"
    try:
        if engine == "parser":
            raw_text = _read_document_text(path)
            raw_result = {"text": raw_text[:2000]}
            base_confidence = 0.95 if raw_text else 0.0
        else:
            raw_text, base_confidence, lines = _call_paddleocr(path, recognition_type)
            raw_result = {"lines": lines, "text": raw_text[:2000]}

        info = _extract_invoice(raw_text) if recognition_type == "invoice" else _extract_contract(raw_text)
        confidence = _confidence_for(info, base_confidence)
        duration = time.perf_counter() - start
        status = "success" if raw_text else "manual_required"
        db.add(
            OcrRecognitionLog(
                file_path=file_path,
                file_name=path.name,
                recognition_type=recognition_type,
                engine=engine,
                raw_result=json.dumps(raw_result, ensure_ascii=False),
                extracted_info=json.dumps(info, ensure_ascii=False),
                confidence=base_confidence,
                status=status,
                duration=duration,
            )
        )
        db.flush()
        return {"raw_text": raw_text[:2000], "extracted_info": info, "confidence": confidence, "engine": engine, "duration": duration, "status": status}
    except Exception as exc:
        duration = time.perf_counter() - start
        db.add(
            OcrRecognitionLog(
                file_path=file_path,
                file_name=path.name,
                recognition_type=recognition_type,
                engine=engine,
                extracted_info=json.dumps({}, ensure_ascii=False),
                confidence=0,
                status="failed",
                duration=duration,
                error_message=str(exc),
            )
        )
        db.flush()
        return {"raw_text": "", "extracted_info": {}, "confidence": {}, "engine": engine, "duration": duration, "status": "failed", "error_message": str(exc)}
