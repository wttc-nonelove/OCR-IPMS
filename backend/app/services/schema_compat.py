from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_compatible_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "project_info" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("project_info")}
    statements: list[str] = []
    if "party_a" not in columns:
        statements.append("ALTER TABLE project_info ADD COLUMN party_a VARCHAR(200)")
    if "party_b" not in columns:
        statements.append("ALTER TABLE project_info ADD COLUMN party_b VARCHAR(200)")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
