from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import (
    APPROVAL_PENDING,
    BALANCE_WAITING,
    PROJECT_DRAFT,
)


class TimestampMixin:
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base, TimestampMixin):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), index=True)
    dept: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[int] = mapped_column(default=1, index=True)


class Role(Base, TimestampMixin):
    __tablename__ = "sys_role"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(String(50))
    role_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    permissions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[int] = mapped_column(default=1)


class DictItem(Base):
    __tablename__ = "sys_dict"
    __table_args__ = (UniqueConstraint("dict_type", "dict_code", name="uk_type_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dict_type: Mapped[str] = mapped_column(String(50), index=True)
    dict_code: Mapped[str] = mapped_column(String(50))
    dict_name: Mapped[str] = mapped_column(String(100))
    sort: Mapped[int] = mapped_column(default=0)
    status: Mapped[int] = mapped_column(default=1)
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SysLog(Base):
    __tablename__ = "sys_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(index=True)
    username: Mapped[str | None] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(50), index=True)
    content: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Project(Base, TimestampMixin):
    __tablename__ = "project_info"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_no: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    customer: Mapped[str] = mapped_column(String(200), index=True)
    party_a: Mapped[str | None] = mapped_column(String(200), index=True)
    party_b: Mapped[str | None] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    contract_no: Mapped[str | None] = mapped_column(String(50))
    sign_date: Mapped[date | None] = mapped_column(Date)
    project_type: Mapped[str | None] = mapped_column(String(50))
    pm_id: Mapped[int | None] = mapped_column(index=True)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    extra_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    cost_desc: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default=PROJECT_DRAFT, index=True)
    balance_status: Mapped[str] = mapped_column(String(20), default=BALANCE_WAITING)
    create_by: Mapped[int | None] = mapped_column(index=True)

    contracts: Mapped[list["Contract"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Contract(Base):
    __tablename__ = "project_contract"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project_info.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(default=1, index=True)
    file_type: Mapped[str] = mapped_column(String(10))
    file_path: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str | None] = mapped_column(String(200))
    file_size: Mapped[int | None]
    upload_by: Mapped[int | None]
    upload_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="contracts")


class ContractDiff(Base):
    __tablename__ = "project_contract_diff"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project_info.id", ondelete="CASCADE"), index=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("project_contract.id", ondelete="CASCADE"), index=True)
    field_name: Mapped[str] = mapped_column(String(50))
    field_label: Mapped[str | None] = mapped_column(String(100))
    registered_value: Mapped[str | None] = mapped_column(Text)
    recognized_value: Mapped[str | None] = mapped_column(Text)
    adopted_value: Mapped[str | None] = mapped_column(Text)
    diff_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    confirm_by: Mapped[int | None]
    confirm_time: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(String(500))
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProjectCost(Base):
    __tablename__ = "project_cost"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project_info.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    description: Mapped[str | None] = mapped_column(String(500))
    create_by: Mapped[int | None]
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Invoice(Base):
    __tablename__ = "project_invoice"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project_info.id", ondelete="CASCADE"), index=True)
    invoice_no: Mapped[str] = mapped_column(String(50), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    invoice_date: Mapped[date] = mapped_column(Date, index=True)
    invoice_type: Mapped[str] = mapped_column(String(20))
    buyer: Mapped[str | None] = mapped_column(String(200))
    seller: Mapped[str | None] = mapped_column(String(200))
    file_path: Mapped[str | None] = mapped_column(String(500))
    create_by: Mapped[int | None]
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="invoices")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")


class Payment(Base):
    __tablename__ = "project_payment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project_info.id", ondelete="CASCADE"), index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("project_invoice.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    payment_method: Mapped[str] = mapped_column(String(20))
    voucher_file: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(String(500))
    create_by: Mapped[int | None]
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="payments")
    invoice: Mapped[Invoice] = relationship(back_populates="payments")


class ProjectClose(Base, TimestampMixin):
    __tablename__ = "project_close"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project_info.id", ondelete="CASCADE"), index=True)
    actual_start: Mapped[date | None] = mapped_column(Date)
    close_time: Mapped[date] = mapped_column(Date)
    report_file: Mapped[str | None] = mapped_column(String(500))
    attachment: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=APPROVAL_PENDING, index=True)
    balance_status: Mapped[str | None] = mapped_column(String(20))
    create_by: Mapped[int | None]


class ApprovalTemplate(Base, TimestampMixin):
    __tablename__ = "approval_template"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_name: Mapped[str] = mapped_column(String(100))
    business_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[int] = mapped_column(default=1)


class ApprovalNode(Base):
    __tablename__ = "approval_node"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("approval_template.id", ondelete="CASCADE"), index=True)
    node_name: Mapped[str] = mapped_column(String(100))
    node_order: Mapped[int]
    approval_type: Mapped[str] = mapped_column(String(20), default="或签")
    timeout_hours: Mapped[int] = mapped_column(default=48)
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ApprovalApprover(Base):
    __tablename__ = "approval_approver"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("approval_node.id", ondelete="CASCADE"), index=True)
    approver_type: Mapped[str] = mapped_column(String(20))
    approver_id: Mapped[str] = mapped_column(String(50))
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ApprovalInstance(Base):
    __tablename__ = "approval_instance"
    __table_args__ = (Index("idx_instance_business", "business_type", "business_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_type: Mapped[str] = mapped_column(String(50))
    business_id: Mapped[int]
    template_id: Mapped[int] = mapped_column(ForeignKey("approval_template.id"), index=True)
    current_node_id: Mapped[int | None] = mapped_column(ForeignKey("approval_node.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=APPROVAL_PENDING, index=True)
    start_by: Mapped[int | None]
    start_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finish_time: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(String(500))


class ApprovalTask(Base):
    __tablename__ = "approval_task"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("approval_instance.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("approval_node.id"), index=True)
    approver_id: Mapped[int] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(20), default=APPROVAL_PENDING, index=True)
    opinion: Mapped[str | None] = mapped_column(String(500))
    reason: Mapped[str | None] = mapped_column(String(500))
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    approve_time: Mapped[datetime | None] = mapped_column(DateTime)


class ApprovalRecord(Base, TimestampMixin):
    __tablename__ = "approval_record"
    __table_args__ = (Index("idx_record_business", "business_type", "business_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instance_id: Mapped[int | None] = mapped_column(ForeignKey("approval_instance.id", ondelete="SET NULL"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("approval_task.id", ondelete="SET NULL"))
    business_type: Mapped[str] = mapped_column(String(50))
    business_id: Mapped[int]
    template_id: Mapped[int | None]
    node_id: Mapped[int | None]
    approver_id: Mapped[int | None] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(20), default=APPROVAL_PENDING, index=True)
    opinion: Mapped[str | None] = mapped_column(String(500))
    reason: Mapped[str | None] = mapped_column(String(500))


class OcrRecognitionLog(Base):
    __tablename__ = "ocr_recognition_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str | None] = mapped_column(String(200))
    recognition_type: Mapped[str] = mapped_column(String(20), index=True)
    engine: Mapped[str] = mapped_column(String(20), index=True)
    raw_result: Mapped[str | None] = mapped_column(Text)
    extracted_info: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(20), index=True)
    duration: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    error_message: Mapped[str | None] = mapped_column(String(500))
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
