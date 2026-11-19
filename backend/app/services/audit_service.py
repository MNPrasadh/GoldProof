"""Append-only hash-chained audit logging service."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.crypto import canonical_json, compute_sha256_hex
from app.models.entities import AuditLog, User

GENESIS_HASH = "0" * 64


def _compute_entry_hash(
    sequence_number: int,
    action: str,
    transaction_id: Optional[str],
    actor_user_id: Optional[str],
    actor_role: str,
    details_json: dict[str, Any],
    previous_log_hash: str,
    created_at: datetime,
) -> str:
    payload = {
        "sequence_number": sequence_number,
        "action": action,
        "transaction_id": transaction_id,
        "actor_user_id": actor_user_id,
        "actor_role": actor_role,
        "details_json": details_json,
        "previous_log_hash": previous_log_hash,
        "created_at": created_at,
    }
    return compute_sha256_hex(canonical_json(payload))


def record_audit_event(
    db: Session,
    action: str,
    actor_user: Optional[User] = None,
    actor_role: Optional[str] = None,
    transaction_id: Optional[str] = None,
    jeweller_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
) -> AuditLog:
    """Append a tamper-evident audit entry chained to the latest entry hash."""
    latest = db.query(AuditLog).order_by(desc(AuditLog.sequence_number)).first()
    next_seq = (latest.sequence_number + 1) if latest else 1
    prev_hash = latest.entry_hash if latest else GENESIS_HASH

    timestamp = (created_at or datetime.now(timezone.utc)).replace(microsecond=0)
    resolved_role = actor_role or (actor_user.role if actor_user else "system")
    resolved_user_id = actor_user.id if actor_user else None
    clean_details = details or {}

    entry_hash = _compute_entry_hash(
        sequence_number=next_seq,
        action=action,
        transaction_id=transaction_id,
        actor_user_id=resolved_user_id,
        actor_role=resolved_role,
        details_json=clean_details,
        previous_log_hash=prev_hash,
        created_at=timestamp,
    )

    log = AuditLog(
        sequence_number=next_seq,
        jeweller_id=jeweller_id,
        transaction_id=transaction_id,
        actor_user_id=resolved_user_id,
        actor_role=resolved_role,
        action=action,
        details_json=clean_details,
        previous_log_hash=prev_hash,
        entry_hash=entry_hash,
        created_at=timestamp,
    )
    db.add(log)
    db.flush()
    return log


def verify_audit_chain(db: Session) -> tuple[bool, int, Optional[int]]:
    """Verify integrity of the entire append-only audit log hash chain.

    Returns (is_valid, total_entries, first_broken_sequence_number).
    """
    logs = db.query(AuditLog).order_by(AuditLog.sequence_number.asc()).all()
    expected_prev = GENESIS_HASH
    for idx, entry in enumerate(logs, start=1):
        if entry.sequence_number != idx or entry.previous_log_hash != expected_prev:
            return False, len(logs), entry.sequence_number
        expected_hash = _compute_entry_hash(
            sequence_number=entry.sequence_number,
            action=entry.action,
            transaction_id=entry.transaction_id,
            actor_user_id=entry.actor_user_id,
            actor_role=entry.actor_role,
            details_json=entry.details_json,
            previous_log_hash=entry.previous_log_hash,
            created_at=entry.created_at,
        )
        if expected_hash != entry.entry_hash:
            return False, len(logs), entry.sequence_number
        expected_prev = entry.entry_hash
    return True, len(logs), None
