from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog


def log(
    db: Session,
    *,
    community_id: int,
    actor_user_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    data: Optional[dict] = None,
) -> AuditLog:
    """Stage an audit record. The calling service owns the commit, so the
    audit row lands in the same transaction as the action it describes."""
    entry = AuditLog(
        community_id=community_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data,
    )
    db.add(entry)
    return entry
