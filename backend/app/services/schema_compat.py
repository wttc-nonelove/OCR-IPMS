from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_compatible_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "project_info" not in tables:
        return
    statements: list[str] = []
    project_columns = {column["name"] for column in inspector.get_columns("project_info")}
    if "party_a" not in project_columns:
        statements.append("ALTER TABLE project_info ADD COLUMN party_a VARCHAR(200)")
    if "party_b" not in project_columns:
        statements.append("ALTER TABLE project_info ADD COLUMN party_b VARCHAR(200)")
    if "project_invoice" in tables:
        invoice_columns = {column["name"] for column in inspector.get_columns("project_invoice")}
        if "amount_without_tax" not in invoice_columns:
            statements.append("ALTER TABLE project_invoice ADD COLUMN amount_without_tax DECIMAL(15, 2) NOT NULL DEFAULT 0")
            statements.append("UPDATE project_invoice SET amount_without_tax = amount WHERE amount_without_tax = 0")
        if "tax_rate" not in invoice_columns:
            statements.append("ALTER TABLE project_invoice ADD COLUMN tax_rate DECIMAL(5, 2) NOT NULL DEFAULT 0")
        if "tax_amount" not in invoice_columns:
            statements.append("ALTER TABLE project_invoice ADD COLUMN tax_amount DECIMAL(15, 2) NOT NULL DEFAULT 0")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
