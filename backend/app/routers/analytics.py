"""Tenant-isolated jeweller analytics and system-level admin analytics router."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_jeweller_profile, require_roles
from app.database import get_db
from app.models.entities import JewellerProfile, User
from app.services.analytics_service import get_admin_analytics, get_jeweller_analytics

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/jeweller")
def jeweller_analytics(
    days: int = Query(default=30, ge=1, le=365),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    jeweller: JewellerProfile = Depends(get_current_jeweller_profile),
    db: Session = Depends(get_db),
):
    """Return analytics strictly scoped to the authenticated jeweller shop."""
    return get_jeweller_analytics(db=db, jeweller=jeweller, days=days, status_filter=status_filter)


@router.get("/admin")
def admin_analytics(
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Return system-level platform aggregates and hash-chained audit logs (Admin only)."""
    return get_admin_analytics(db=db)
