"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-06-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sys_user
    op.create_table(
        "sys_user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("dept", sa.String(50), nullable=True),
        sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("update_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sys_user_username", "sys_user", ["username"], unique=True)
    op.create_index("ix_sys_user_role", "sys_user", ["role"])
    op.create_index("ix_sys_user_status", "sys_user", ["status"])

    # sys_role
    op.create_table(
        "sys_role",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_name", sa.String(50), nullable=False),
        sa.Column("role_code", sa.String(50), nullable=False),
        sa.Column("permissions", sa.Text(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("update_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sys_role_role_code", "sys_role", ["role_code"], unique=True)

    # sys_dict
    op.create_table(
        "sys_dict",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dict_type", sa.String(50), nullable=False),
        sa.Column("dict_code", sa.String(50), nullable=False),
        sa.Column("dict_name", sa.String(100), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dict_type", "dict_code", name="uk_type_code"),
    )
    op.create_index("ix_sys_dict_dict_type", "sys_dict", ["dict_type"])

    # sys_log
    op.create_table(
        "sys_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(50), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("ip", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sys_log_user_id", "sys_log", ["user_id"])
    op.create_index("ix_sys_log_action", "sys_log", ["action"])
    op.create_index("ix_sys_log_create_time", "sys_log", ["create_time"])

    # project_info
    op.create_table(
        "project_info",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_no", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("customer", sa.String(200), nullable=False),
        sa.Column("party_a", sa.String(200), nullable=True),
        sa.Column("party_b", sa.String(200), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("contract_no", sa.String(50), nullable=True),
        sa.Column("sign_date", sa.Date(), nullable=True),
        sa.Column("project_type", sa.String(50), nullable=True),
        sa.Column("pm_id", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("extra_cost", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("cost_desc", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("balance_status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("create_by", sa.Integer(), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("update_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_info_project_no", "project_info", ["project_no"], unique=True)
    op.create_index("ix_project_info_customer", "project_info", ["customer"])
    op.create_index("ix_project_info_party_a", "project_info", ["party_a"])
    op.create_index("ix_project_info_pm_id", "project_info", ["pm_id"])
    op.create_index("ix_project_info_status", "project_info", ["status"])
    op.create_index("ix_project_info_create_by", "project_info", ["create_by"])

    # project_contract
    op.create_table(
        "project_contract",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project_info.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(200), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("upload_by", sa.Integer(), nullable=True),
        sa.Column("upload_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_contract_project_id", "project_contract", ["project_id"])
    op.create_index("ix_project_contract_version", "project_contract", ["version"])

    # project_contract_diff
    op.create_table(
        "project_contract_diff",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project_info.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("project_contract.id", ondelete="CASCADE"), nullable=True),
        sa.Column("field_name", sa.String(50), nullable=False),
        sa.Column("field_label", sa.String(100), nullable=True),
        sa.Column("registered_value", sa.Text(), nullable=True),
        sa.Column("recognized_value", sa.Text(), nullable=True),
        sa.Column("adopted_value", sa.Text(), nullable=True),
        sa.Column("diff_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("confirm_by", sa.Integer(), nullable=True),
        sa.Column("confirm_time", sa.DateTime(), nullable=True),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_contract_diff_project_id", "project_contract_diff", ["project_id"])
    op.create_index("ix_project_contract_diff_contract_id", "project_contract_diff", ["contract_id"])
    op.create_index("ix_project_contract_diff_diff_status", "project_contract_diff", ["diff_status"])

    # project_cost
    op.create_table(
        "project_cost",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project_info.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("create_by", sa.Integer(), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_cost_project_id", "project_cost", ["project_id"])

    # project_invoice
    op.create_table(
        "project_invoice",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project_info.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_no", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("invoice_type", sa.String(20), nullable=False),
        sa.Column("buyer", sa.String(200), nullable=True),
        sa.Column("seller", sa.String(200), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("create_by", sa.Integer(), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_invoice_project_id", "project_invoice", ["project_id"])
    op.create_index("ix_project_invoice_invoice_no", "project_invoice", ["invoice_no"], unique=True)
    op.create_index("ix_project_invoice_invoice_date", "project_invoice", ["invoice_date"])

    # project_payment
    op.create_table(
        "project_payment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project_info.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("project_invoice.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("voucher_file", sa.String(500), nullable=True),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("create_by", sa.Integer(), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_payment_project_id", "project_payment", ["project_id"])
    op.create_index("ix_project_payment_invoice_id", "project_payment", ["invoice_id"])
    op.create_index("ix_project_payment_payment_date", "project_payment", ["payment_date"])

    # project_close
    op.create_table(
        "project_close",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project_info.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actual_start", sa.Date(), nullable=True),
        sa.Column("close_time", sa.Date(), nullable=False),
        sa.Column("report_file", sa.String(500), nullable=True),
        sa.Column("attachment", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("balance_status", sa.String(20), nullable=True),
        sa.Column("create_by", sa.Integer(), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("update_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_close_project_id", "project_close", ["project_id"])
    op.create_index("ix_project_close_status", "project_close", ["status"])

    # approval_template
    op.create_table(
        "approval_template",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_name", sa.String(100), nullable=False),
        sa.Column("business_type", sa.String(50), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("update_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_template_business_type", "approval_template", ["business_type"])

    # approval_node
    op.create_table(
        "approval_node",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("approval_template.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_name", sa.String(100), nullable=False),
        sa.Column("node_order", sa.Integer(), nullable=False),
        sa.Column("approval_type", sa.String(20), nullable=False, server_default="或签"),
        sa.Column("timeout_hours", sa.Integer(), nullable=False, server_default="48"),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_node_template_id", "approval_node", ["template_id"])

    # approval_approver
    op.create_table(
        "approval_approver",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.Integer(), sa.ForeignKey("approval_node.id", ondelete="CASCADE"), nullable=False),
        sa.Column("approver_type", sa.String(20), nullable=False),
        sa.Column("approver_id", sa.String(50), nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_approver_node_id", "approval_approver", ["node_id"])

    # approval_instance
    op.create_table(
        "approval_instance",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("business_type", sa.String(50), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("approval_template.id"), nullable=False),
        sa.Column("current_node_id", sa.Integer(), sa.ForeignKey("approval_node.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("start_by", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("finish_time", sa.DateTime(), nullable=True),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_instance_template_id", "approval_instance", ["template_id"])
    op.create_index("ix_approval_instance_current_node_id", "approval_instance", ["current_node_id"])
    op.create_index("ix_approval_instance_status", "approval_instance", ["status"])
    op.create_index("idx_instance_business", "approval_instance", ["business_type", "business_id"])

    # approval_task
    op.create_table(
        "approval_task",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("approval_instance.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", sa.Integer(), sa.ForeignKey("approval_node.id"), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("opinion", sa.String(500), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("approve_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_task_instance_id", "approval_task", ["instance_id"])
    op.create_index("ix_approval_task_node_id", "approval_task", ["node_id"])
    op.create_index("ix_approval_task_approver_id", "approval_task", ["approver_id"])
    op.create_index("ix_approval_task_status", "approval_task", ["status"])

    # approval_record
    op.create_table(
        "approval_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("approval_instance.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("approval_task.id", ondelete="SET NULL"), nullable=True),
        sa.Column("business_type", sa.String(50), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("node_id", sa.Integer(), nullable=True),
        sa.Column("approver_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("opinion", sa.String(500), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("update_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_record_approver_id", "approval_record", ["approver_id"])
    op.create_index("ix_approval_record_status", "approval_record", ["status"])
    op.create_index("idx_record_business", "approval_record", ["business_type", "business_id"])

    # ocr_recognition_log
    op.create_table(
        "ocr_recognition_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(200), nullable=True),
        sa.Column("recognition_type", sa.String(20), nullable=False),
        sa.Column("engine", sa.String(20), nullable=False),
        sa.Column("raw_result", sa.Text(), nullable=True),
        sa.Column("extracted_info", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("duration", sa.Numeric(10, 3), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ocr_recognition_log_recognition_type", "ocr_recognition_log", ["recognition_type"])
    op.create_index("ix_ocr_recognition_log_engine", "ocr_recognition_log", ["engine"])
    op.create_index("ix_ocr_recognition_log_status", "ocr_recognition_log", ["status"])
    op.create_index("ix_ocr_recognition_log_create_time", "ocr_recognition_log", ["create_time"])


def downgrade() -> None:
    op.drop_table("ocr_recognition_log")
    op.drop_table("approval_record")
    op.drop_table("approval_task")
    op.drop_table("approval_instance")
    op.drop_table("approval_approver")
    op.drop_table("approval_node")
    op.drop_table("approval_template")
    op.drop_table("project_close")
    op.drop_table("project_payment")
    op.drop_table("project_invoice")
    op.drop_table("project_cost")
    op.drop_table("project_contract_diff")
    op.drop_table("project_contract")
    op.drop_table("project_info")
    op.drop_table("sys_log")
    op.drop_table("sys_dict")
    op.drop_table("sys_role")
    op.drop_table("sys_user")
