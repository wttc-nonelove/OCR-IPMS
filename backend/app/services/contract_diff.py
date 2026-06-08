"""合同差异比对服务"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models.entities import ContractDiff, DictItem, Project


def diff_out(d: ContractDiff) -> dict:
    """将 ContractDiff 对象转换为输出字典"""
    return {
        "id": d.id,
        "field_name": d.field_name,
        "field_label": d.field_label,
        "registered_value": d.registered_value,
        "recognized_value": d.recognized_value,
        "adopted_value": d.adopted_value,
        "diff_status": d.diff_status,
        "confirm_by": d.confirm_by,
        "confirm_time": d.confirm_time.isoformat() if d.confirm_time else None,
        "remark": d.remark,
        "create_time": d.create_time.isoformat() if d.create_time else None,
    }


def display_value(db: Session, field_name: str, value) -> str:
    """将字段值转换为显示用的文本"""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if field_name == "amount":
        try:
            return f"{Decimal(text.replace(',', '')).quantize(Decimal('0.01'))}"
        except (InvalidOperation, AttributeError):
            return text
    if field_name == "project_type":
        item = db.query(DictItem).filter(
            DictItem.dict_type == "project_type",
            (DictItem.dict_code == text) | (DictItem.dict_name == text),
        ).first()
        return item.dict_name if item else text
    return " ".join(text.split())


def normalize_compare_value(db: Session, field_name: str, value: str) -> str:
    """规范化比较值（用于差异比对）"""
    text = display_value(db, field_name, value)
    if field_name == "amount":
        return text
    if field_name == "project_type":
        item = db.query(DictItem).filter(
            DictItem.dict_type == "project_type",
            (DictItem.dict_code == value) | (DictItem.dict_name == value),
        ).first()
        return (item.dict_name if item else value).strip().lower()
    import re
    return re.sub(r"\s+", "", text).strip().lower()


def create_contract_diffs(
    db: Session, project: Project, contract_id: int, extracted: dict
) -> tuple[list[ContractDiff], list[dict]]:
    """创建合同差异记录

    Returns:
        (创建的差异列表, 未识别的字段列表)
    """
    comparisons = [
        ("name", "项目名称", project.name, extracted.get("project_name")),
        ("party_a", "甲方/客户", project.party_a or project.customer, extracted.get("party_a") or extracted.get("customer")),
        ("party_b", "乙方", project.party_b, extracted.get("party_b")),
        ("amount", "合同金额", str(project.amount), extracted.get("contract_amount")),
        ("contract_no", "合同编号", project.contract_no, extracted.get("contract_no")),
        ("sign_date", "签订日期", project.sign_date.isoformat() if project.sign_date else None, extracted.get("sign_date")),
        ("project_type", "项目类型", project.project_type, extracted.get("project_type")),
    ]
    created = []
    unrecognized = []
    for field_name, label, registered, recognized in comparisons:
        registered_text = display_value(db, field_name, registered)
        recognized_text = display_value(db, field_name, recognized)
        if not recognized_text:
            if registered_text:
                unrecognized.append({"field_name": field_name, "field_label": label, "registered_value": registered_text})
            continue
        if normalize_compare_value(db, field_name, registered_text) == normalize_compare_value(db, field_name, recognized_text):
            continue
        diff = ContractDiff(
            project_id=project.id,
            contract_id=contract_id,
            field_name=field_name,
            field_label=label,
            registered_value=registered_text,
            recognized_value=recognized_text,
            adopted_value=recognized_text,
            diff_status="pending",
        )
        db.add(diff)
        created.append(diff)
    db.flush()
    return created, unrecognized


def apply_diff_value(project: Project, field_name: str, value: str, db: Session) -> None:
    """将差异确认的值应用到项目"""
    if field_name == "name":
        project.name = value
    elif field_name == "party_a":
        project.party_a = value
        project.customer = value
    elif field_name == "party_b":
        project.party_b = value
    elif field_name == "amount":
        try:
            project.amount = Decimal(value)
        except Exception:
            return
    elif field_name == "contract_no":
        project.contract_no = value
    elif field_name == "sign_date":
        try:
            project.sign_date = date.fromisoformat(value)
        except ValueError:
            return
    elif field_name == "project_type":
        from app.services.project_type import ensure_project_type
        project.project_type = ensure_project_type(db, value)
