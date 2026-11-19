"""Authentication, JWT tokens, password hashing, and strict RBAC / tenant isolation."""

from datetime import datetime, timedelta, timezone
from typing import Callable

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.entities import JewellerProfile, Transaction, User

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user: User) -> str:
    """Mint a signed JWT token containing subject, role, and expiry."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "role": user.role,
        "email": user.email,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate an incoming JWT token."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve authenticated active user from Bearer token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed authentication token.")

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found or inactive.")
    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """Role-based access control dependency factory."""

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to roles: {', '.join(allowed_roles)}.",
            )
        return current_user

    return _checker


def get_current_jeweller_profile(
    current_user: User = Depends(require_roles("jeweller")),
    db: Session = Depends(get_db),
) -> JewellerProfile:
    """Resolve the JewellerProfile owned by the authenticated jeweller user."""
    profile = db.query(JewellerProfile).filter(JewellerProfile.user_id == current_user.id).first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller shop profile is not configured for this account.",
        )
    return profile


def assert_transaction_access(db: Session, user: User, tx: Transaction) -> None:
    """Enforce strict tenant isolation for jewellers and ownership isolation for customers."""
    if user.role == "admin":
        return

    if user.role == "jeweller":
        profile = db.query(JewellerProfile).filter(JewellerProfile.user_id == user.id).first()
        if profile is None or tx.jeweller_id != profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant isolation enforced: you cannot access another jeweller's transaction.",
            )
        return

    if user.role == "customer":
        owns_by_user_id = tx.customer_user_id == user.id
        owns_by_phone = bool(
            user.phone
            and tx.customer_profile is not None
            and tx.customer_profile.mobile_number == user.phone
        )
        if not (owns_by_user_id or owns_by_phone):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: this transaction belongs to a different customer.",
            )
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
