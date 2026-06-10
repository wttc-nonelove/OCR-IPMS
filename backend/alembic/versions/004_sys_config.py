"""add system config

Revision ID: 004_sys_config
Revises: 003_payment_invoice_nullable
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_sys_config"
down_revision: Union[str, None] = "003_payment_invoice_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sys_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("config_key", sa.String(100), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=True),
        sa.Column("config_type", sa.String(50), nullable=False, server_default="system"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_secret", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("update_by", sa.Integer(), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("update_time", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sys_config_config_key", "sys_config", ["config_key"], unique=True)
    op.create_index("ix_sys_config_config_type", "sys_config", ["config_type"])
    op.create_index("ix_sys_config_update_by", "sys_config", ["update_by"])
    op.bulk_insert(
        sa.table(
            "sys_config",
            sa.column("config_key", sa.String),
            sa.column("config_value", sa.Text),
            sa.column("config_type", sa.String),
            sa.column("description", sa.String),
            sa.column("is_secret", sa.Integer),
        ),
        [
            {"config_key": "LLM_ENABLED", "config_value": "false", "config_type": "llm", "description": "是否启用大模型合同解析兜底", "is_secret": 0},
            {"config_key": "LLM_ACTIVE_PROFILE", "config_value": "default", "config_type": "llm", "description": "当前使用的大模型配置 ID", "is_secret": 0},
            {"config_key": "LLM_PROFILES", "config_value": "[]", "config_type": "llm", "description": "大模型配置列表", "is_secret": 1},
            {"config_key": "LLM_API_KEY", "config_value": "", "config_type": "llm", "description": "OpenAI 兼容接口 API Key", "is_secret": 1},
            {"config_key": "LLM_API_BASE_URL", "config_value": "https://api.openai.com/v1", "config_type": "llm", "description": "OpenAI 兼容接口地址", "is_secret": 0},
            {"config_key": "LLM_MODEL", "config_value": "gpt-4o-mini", "config_type": "llm", "description": "大模型名称", "is_secret": 0},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_sys_config_update_by", table_name="sys_config")
    op.drop_index("ix_sys_config_config_type", table_name="sys_config")
    op.drop_index("ix_sys_config_config_key", table_name="sys_config")
    op.drop_table("sys_config")
