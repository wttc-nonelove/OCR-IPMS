from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ProjectOut(BaseModel):
    id: int
    project_no: str
    name: str
    customer: str
    amount: Decimal
    status: str
    balance_status: str
    contract_no: str | None = None
    sign_date: date | None = None
    project_type: str | None = None
    pm_id: int | None = None
    create_time: datetime

    class Config:
        from_attributes = True


class ApprovalProcessIn(BaseModel):
    task_id: int
    result: str
    opinion: str | None = None
    reason: str | None = None


class ContractDiffConfirmIn(BaseModel):
    diff_id: int
    adopted_value: str | None = None
    diff_status: str = "confirmed"
    remark: str | None = None


class ProjectStartIn(BaseModel):
    project_id: int
    remark: str | None = None


class ProjectApproveIn(BaseModel):
    project_id: int
    result: str
    opinion: str | None = None
    reason: str | None = None


class CloseWithdrawIn(BaseModel):
    project_id: int
    reason: str
