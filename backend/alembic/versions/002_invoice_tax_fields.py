"""add invoice tax fields

Revision ID: 002_invoice_tax
Revises: 001_initial
Create Date: 2026-06-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_invoice_tax"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_invoice", sa.Column("amount_without_tax", sa.Numeric(15, 2), nullable=False, server_default="0"))
    op.add_column("project_invoice", sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0"))
    op.add_column("project_invoice", sa.Column("tax_amount", sa.Numeric(15, 2), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("project_invoice", "tax_amount")
    op.drop_column("project_invoice", "tax_rate")
    op.drop_column("project_invoice", "amount_without_tax")
