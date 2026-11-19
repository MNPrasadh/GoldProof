"""Low-connectivity PWA offline draft synchronization router with conflict protection."""

from datetime import timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_jeweller_profile, require_roles
from app.database import get_db
from app.models.entities import JewellerProfile, Transaction, User
from app.schemas.transaction import (
    OfflineSyncBatchRequest,
    OfflineSyncBatchResponse,
    OfflineSyncResultItem,
)
from app.services.transaction_service import (
    create_transaction_record,
    load_transaction_full,
    update_mutable_transaction,
)

router = APIRouter(prefix="/api/sync", tags=["Offline Sync"])


def _to_utc(dt):
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


@router.post("/drafts", response_model=OfflineSyncBatchResponse)
def sync_offline_drafts(
    batch: OfflineSyncBatchRequest,
    jeweller: JewellerProfile = Depends(get_current_jeweller_profile),
    current_user: User = Depends(require_roles("jeweller")),
    db: Session = Depends(get_db),
):
    """Synchronize queued offline drafts cleanly without ever overwriting signed records."""
    results: list[OfflineSyncResultItem] = []

    for item in batch.drafts:
        client_ts = _to_utc(item.client_updated_at)
        existing = (
            db.query(Transaction)
            .filter(Transaction.client_draft_id == item.client_draft_id)
            .first()
        )

        if existing is None:
            payload = item.payload.model_copy(
                update={
                    "client_draft_id": item.client_draft_id,
                    "client_updated_at": client_ts,
                }
            )
            created = create_transaction_record(
                db=db,
                jeweller=jeweller,
                actor_user=current_user,
                payload=payload,
            )
            results.append(
                OfflineSyncResultItem(
                    client_draft_id=item.client_draft_id,
                    status="created",
                    transaction_id=created.id,
                    transaction_code=created.transaction_code,
                    message="Offline draft synchronized and stored on server (pending signing).",
                )
            )
            continue

        # Enforce tenant isolation even on draft ID collision
        if existing.jeweller_id != jeweller.id:
            results.append(
                OfflineSyncResultItem(
                    client_draft_id=item.client_draft_id,
                    status="validation_error",
                    message="Draft identifier belongs to another shop tenant.",
                )
            )
            continue

        # Never silently overwrite a signed or amended transaction
        if existing.status in ("signed", "amended") or existing.digital_passport is not None:
            results.append(
                OfflineSyncResultItem(
                    client_draft_id=item.client_draft_id,
                    status="conflict_signed_immutable",
                    transaction_id=existing.id,
                    transaction_code=existing.transaction_code,
                    message=(
                        f"Conflict: Transaction {existing.transaction_code} is already cryptographically signed "
                        "and immutable. Offline changes were not applied."
                    ),
                )
            )
            continue

        # Compare timestamps to avoid clobbering newer server edits
        if existing.client_updated_at and client_ts == _to_utc(existing.client_updated_at):
            results.append(
                OfflineSyncResultItem(
                    client_draft_id=item.client_draft_id,
                    status="already_synced",
                    transaction_id=existing.id,
                    transaction_code=existing.transaction_code,
                    message="Offline draft already synchronized with identical timestamp.",
                )
            )
            continue

        if existing.updated_at and client_ts < _to_utc(existing.updated_at):
            results.append(
                OfflineSyncResultItem(
                    client_draft_id=item.client_draft_id,
                    status="conflict_server_newer",
                    transaction_id=existing.id,
                    transaction_code=existing.transaction_code,
                    message=(
                        f"Conflict: Server version of {existing.transaction_code} was updated more recently "
                        f"({existing.updated_at.isoformat()}). Review server record before overwriting."
                    ),
                )
            )
            continue

        full = load_transaction_full(db, existing.id)
        payload = item.payload.model_copy(
            update={
                "client_draft_id": item.client_draft_id,
                "client_updated_at": client_ts,
            }
        )
        updated = update_mutable_transaction(db, full, jeweller, current_user, payload)  # type: ignore[arg-type]
        results.append(
            OfflineSyncResultItem(
                client_draft_id=item.client_draft_id,
                status="updated",
                transaction_id=updated.id,
                transaction_code=updated.transaction_code,
                message="Existing pending draft updated cleanly from offline queue.",
            )
        )

    return OfflineSyncBatchResponse(results=results)
