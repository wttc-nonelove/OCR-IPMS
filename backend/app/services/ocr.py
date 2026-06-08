import json
import re
import time
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx
from docx import Document
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import OcrRecognitionLog


_CN_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "壹": 1,
    "二": 2,
    "贰": 2,
    "两": 2,
    "三": 3,
    "叁": 3,
    "四": 4,
    "肆": 4,
    "五": 5,
    "伍": 5,
    "六": 6,
    "陆": 6,
    "七": 7,
    "柒": 7,
    "八": 8,
    "捌": 8,
    "九": 9,
    "玖": 9,
}
_CN_UNITS = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000}


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return text.replace("\u3000", " ").replace("\r\n", "\n").replace("\r", "\n")


def _clean_value(value: str | None, limit: int = 120) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value)
    value = re.split(r"[\n\r;；]", value, 1)[0]
    value = re.split(r"[（(]以下简称", value, 1)[0]
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t:：,，.。)）(（[]【】\"'").strip()[:limit]


def _decimal_text(value: str | None) -> str:
    if not value:
        return ""
    try:
        return f"{Decimal(value.replace(',', '')).quantize(Decimal('0.01'))}"
    except (InvalidOperation, AttributeError):
        return ""


def _parse_chinese_section(section: str) -> int:
    total = 0
    number = 0
    for char in section:
        if char in _CN_DIGITS:
            number = _CN_DIGITS[char]
        elif char in _CN_UNITS:
            total += (number or 1) * _CN_UNITS[char]
            number = 0
    return total + number


def _parse_chinese_integer(value: str) -> int:
    value = re.sub(r"[人民币圆元整正\s]", "", value)
    value = re.split(r"[角分]", value, 1)[0]
    total = 0
    if "亿" in value:
        before, value = value.split("亿", 1)
        total += _parse_chinese_section(before) * 100000000
    if "万" in value:
        before, value = value.split("万", 1)
        total += _parse_chinese_section(before) * 10000
    total += _parse_chinese_section(value)
    return total


def _extract_chinese_amount(text: str) -> str:
    amount_chars = "零〇一壹二贰两三叁四肆五伍六陆七柒八捌九玖十拾百佰千仟万亿圆元角分整正"
    patterns = [
        rf"(?:合同金额|合同总金额|总金额|价款|金额|人民币)[:：\s]*(?:人民币)?\s*([{amount_chars}]{{2,}})",
        rf"人民币\s*([{amount_chars}]{{2,}})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        amount = _parse_chinese_integer(match.group(1))
        if amount:
            return f"{Decimal(amount).quantize(Decimal('0.01'))}"
    return ""


def _extract_amount(text: str, labels: list[str] | None = None) -> str:
    text = _normalize_text(text)
    labels = labels or ["合同金额", "合同总金额", "总金额", "价款", "金额", "人民币"]
    label_expr = "|".join(re.escape(label) for label in labels)
    labeled_patterns = [
        rf"(?:{label_expr})[:：\s]*(?:人民币)?[^\n\r\d¥￥]{{0,40}}[（(]?\s*[¥￥]\s*([0-9][0-9,]*(?:\.\d{{1,2}})?)",
        rf"(?:{label_expr})[:：\s]*(?:人民币)?\s*([0-9][0-9,]*(?:\.\d{{1,2}})?)",
        rf"(?:{label_expr})[:：\s]*(?:人民币)?[^\n\r\d]{{0,80}}([0-9][0-9,]*(?:\.\d{{1,2}})?)",
    ]
    for pattern in labeled_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            amount = _decimal_text(match.group(1))
            if amount:
                return amount

    symbol_matches = re.findall(r"[¥￥]\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text)
    if symbol_matches:
        amounts = [_decimal_text(item) for item in symbol_matches]
        amounts = [item for item in amounts if item]
        if amounts:
            return max(amounts, key=lambda item: Decimal(item))

    chinese = _extract_chinese_amount(text)
    if chinese:
        return chinese

    candidates = []
    for match in re.finditer(r"\b([0-9][0-9,]*(?:\.\d{1,2})?)\b", text):
        raw = match.group(1)
        if re.fullmatch(r"20\d{2}", raw):
            continue
        amount = _decimal_text(raw)
        if amount:
            candidates.append(amount)
    return max(candidates, key=lambda item: Decimal(item)) if candidates else ""


def _extract_date(text: str) -> str:
    text = _normalize_text(text)
    match = re.search(r"(20\d{2})[年\-/\.](\d{1,2})[月\-/\.](\d{1,2})日?", text)
    if not match:
        return ""
    return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"


def _match_after(text: str, labels: list[str], limit: int = 120) -> str:
    text = _normalize_text(text)
    for line in re.split(r"[\n\r]+", text):
        normalized = line.strip()
        for label in labels:
            match = re.search(rf"{re.escape(label)}(?:[（(][^）)]*[）)])?\s*[:：]?\s*(.+)$", normalized)
            if match:
                return _clean_value(match.group(1), limit)
    for label in labels:
        match = re.search(rf"{re.escape(label)}(?:[（(][^）)]*[）)])?\s*[:：]?\s*([^\n\r;；]{{1,{limit}}})", text)
        if match:
            return _clean_value(match.group(1), limit)
    return ""


def _extract_contract_no(text: str) -> str:
    text = _normalize_text(text)
    labeled = _match_after(text, ["合同编号", "合同号", "编号"], 80)
    if labeled:
        match = re.search(r"[A-Za-z0-9][A-Za-z0-9\-_]{3,}", labeled)
        return match.group(0) if match else labeled
    match = re.search(r"\b(HT[-_A-Za-z0-9]{4,}|PRJ[-_A-Za-z0-9]{4,})\b", text, re.I)
    return match.group(1) if match else ""


def _extract_invoice_no(text: str) -> str:
    text = _normalize_text(text)
    labeled = _match_after(text, ["发票号码", "发票号", "号码"], 80)
    if labeled:
        match = re.search(r"[A-Za-z0-9-]{6,30}", labeled)
        return match.group(0) if match else labeled
    match = re.search(r"(?:发票号码|发票号|No\.?)\s*[:：]?\s*([A-Za-z0-9-]{6,30})", text, re.I)
    return match.group(1) if match else ""


def _extract_contract(text: str) -> dict:
    text = _normalize_text(text)
    party_a = _match_after(text, ["甲方", "委托方", "采购方", "客户名称", "客户"])
    party_b = _match_after(text, ["乙方", "承包方", "服务方", "供应商"])
    return {
        "project_name": _match_after(text, ["项目名称", "项目名", "项目"]),
        "contract_amount": _extract_amount(text, ["合同金额", "合同总金额", "总金额", "价款", "金额", "人民币"]),
        "contract_no": _extract_contract_no(text),
        "sign_date": _extract_date(text),
        "party_a": party_a,
        "party_b": party_b,
        "customer": party_a,
        "project_type": _match_after(text, ["项目类型", "业务类型", "服务类型", "合同类型"], 50),
    }


def _extract_invoice(text: str) -> dict:
    text = _normalize_text(text)
    # 价税合计（发票总金额）
    amount = _extract_amount(text, ["价税合计", "合计金额", "发票金额", "开票金额"])
    # 不含税金额（发票上的"金额"栏）
    amount_without_tax = _extract_amount(text, ["金额"])
    # 税额
    tax_amount = _extract_amount(text, ["税额"])
    # 税率（百分比文本，如 "13%"）
    tax_rate = ""
    rate_match = re.search(r"税率?\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%", text)
    if rate_match:
        tax_rate = rate_match.group(1)
    else:
        # 尝试从税额和不含税金额反算税率
        if tax_amount and amount_without_tax:
            try:
                ta = Decimal(tax_amount)
                awt = Decimal(amount_without_tax)
                if awt > 0:
                    tax_rate = f"{(ta / awt * 100).quantize(Decimal('0.01'))}"
            except (InvalidOperation, ZeroDivisionError):
                pass

    return {
        "invoice_no": _extract_invoice_no(text),
        "amount": amount,
        "amount_without_tax": amount_without_tax,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "invoice_date": _extract_date(text),
        "buyer": _match_after(text, ["购买方名称", "购买方", "购方", "买方"]),
        "seller": _match_after(text, ["销售方名称", "销售方", "销方", "卖方"]),
    }


def _extract_payment(text: str) -> dict:
    text = _normalize_text(text)
    payer = _match_after(text, ["付款方", "付款人", "付款账户名", "付款单位", "汇款方"])
    payee = _match_after(text, ["收款方", "收款人", "收款账户名", "收款单位"])
    serial = _match_after(text, ["流水号", "交易流水号", "回单编号", "凭证号"], 80)
    return {
        "amount": _extract_amount(text, ["回款金额", "付款金额", "收款金额", "交易金额", "金额", "人民币"]),
        "payment_date": _extract_date(text),
        "payer": payer,
        "payee": payee,
        "serial_no": serial,
        "remark": serial or payer or payee,
    }


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
        response = httpx.post(settings.paddleocr_url, params={"type": recognition_type}, files=files, timeout=90)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data", payload)
    if payload.get("code") not in {None, 200, "200"}:
        raise RuntimeError(data.get("error") or payload.get("message") or "PaddleOCR 识别失败")

    raw_lines = data.get("lines") or []
    raw_text_field = data.get("raw_text") or data.get("text") or ""
    texts: list[str] = []
    confidences: list[float] = []
    for line in raw_lines:
        if isinstance(line, dict):
            if not raw_text_field:
                texts.append(str(line.get("text") or ""))
            if line.get("confidence") is not None:
                confidences.append(float(line["confidence"]))
        elif isinstance(line, (list, tuple)) and line:
            if not raw_text_field:
                texts.append(str(line[0]))
            if len(line) >= 3:
                try:
                    confidences.append(float(line[2]))
                except (TypeError, ValueError):
                    pass
        elif not raw_text_field:
            texts.append(str(line))
    raw_text = raw_text_field if isinstance(raw_text_field, str) and raw_text_field else "\n".join(t for t in texts if t)
    confidence = sum(confidences) / len(confidences) if confidences else float(data.get("confidence") or 0)
    return raw_text, confidence, raw_lines


def _extract_by_type(raw_text: str, recognition_type: str) -> dict:
    if recognition_type == "invoice":
        return _extract_invoice(raw_text)
    if recognition_type == "payment":
        return _extract_payment(raw_text)
    return _extract_contract(raw_text)


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

        info = _extract_by_type(raw_text, recognition_type)
        confidence = _confidence_for(info, base_confidence)
        duration = time.perf_counter() - start
        status = "success" if raw_text else "manual_required"
        log = OcrRecognitionLog(
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
        db.add(log)
        db.flush()
        return {"log_id": log.id, "raw_text": raw_text[:2000], "extracted_info": info, "confidence": confidence, "engine": engine, "duration": duration, "status": status}
    except Exception as exc:
        duration = time.perf_counter() - start
        log = OcrRecognitionLog(
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
        db.add(log)
        db.flush()
        return {"log_id": log.id, "raw_text": "", "extracted_info": {}, "confidence": {}, "engine": engine, "duration": duration, "status": "failed", "error_message": str(exc)}
