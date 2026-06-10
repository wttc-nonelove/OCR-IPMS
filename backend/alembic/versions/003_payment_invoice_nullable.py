"""make payment invoice nullable

Revision ID: 003_payment_invoice_nullable
Revises: 002_invoice_tax
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "003_payment_invoice_nullable"
down_revision: Union[str, None] = "002_invoice_tax"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _invoice_fk_names(bind) -> list[str]:
    inspector = inspect(bind)
    names: list[str] = []
    for fk in inspector.get_foreign_keys("project_payment"):
        if fk.get("referred_table") == "project_invoice" and "invoice_id" in (fk.get("constrained_columns") or []):
            if fk.get("name"):
                names.append(fk["name"])
    return names


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        for fk_name in _invoice_fk_names(bind):
            op.drop_constraint(fk_name, "project_payment", type_="foreignkey")
        op.alter_column("project_payment", "invoice_id", existing_type=sa.Integer(), nullable=True)
        op.create_foreign_key("fk_project_payment_invoice", "project_payment", "project_invoice", ["invoice_id"], ["id"], ondelete="SET NULL")
    else:
        with op.batch_alter_table("project_payment") as batch_op:
            batch_op.alter_column("invoice_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        for fk_name in _invoice_fk_names(bind):
            op.drop_constraint(fk_name, "project_payment", type_="foreignkey")
        op.alter_column("project_payment", "invoice_id", existing_type=sa.Integer(), nullable=False)
        op.create_foreign_key("fk_project_payment_invoice", "project_payment", "project_invoice", ["invoice_id"], ["id"], ondelete="RESTRICT")
    else:
        with op.batch_alter_table("project_payment") as batch_op:
            batch_op.alter_column("invoice_id", existing_type=sa.Integer(), nullable=False)
