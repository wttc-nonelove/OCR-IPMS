from sqlalchemy.orm import Session

from app.models.entities import SysLog, User


def log_action(db: Session, user: User | None, action: str, content: str | None = None) -> None:
    db.add(
        SysLog(
            user_id=user.id if user else None,
            username=user.username if user else None,
            action=action,
            content=content,
        )
    )
