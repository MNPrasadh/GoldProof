"""Authentication, registration, and demo accounts router."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.entities import JewellerProfile, User
from app.schemas.auth import (
    DemoAccountOut,
    JewellerProfileOut,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.audit_service import record_audit_event
from app.services.seed import get_demo_accounts_catalog

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _serialize_user(user: User) -> UserOut:
    jp = user.jeweller_profile
    return UserOut(
        id=user.id,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        preferred_language=user.preferred_language,
        is_demo=bool(user.is_demo),
        jeweller_profile=JewellerProfileOut(
            id=jp.id,
            shop_name=jp.shop_name,
            shop_code=jp.shop_code,
            city=jp.city,
            state=jp.state,
            bis_hallmark_license=jp.bis_hallmark_license,
            policy_max_deduction_pct=str(jp.policy_max_deduction_pct),
            policy_max_wastage_pct=str(jp.policy_max_wastage_pct),
            policy_max_fixed_deduction_inr=str(jp.policy_max_fixed_deduction_inr),
            policy_notes=jp.policy_notes,
        )
        if jp
        else None,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password and receive a JWT access token."""
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

    token = create_access_token(user)
    return TokenResponse(access_token=token, user=_serialize_user(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new jeweller or customer account."""
    clean_email = payload.email.lower().strip()
    if db.query(User).filter(User.email == clean_email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")

    clean_phone = payload.phone.strip() if payload.phone else None
    if clean_phone and db.query(User).filter(User.phone == clean_phone).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mobile number is already registered.")

    user = User(
        email=clean_email,
        phone=clean_phone,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        preferred_language=payload.preferred_language,
        is_demo=False,
    )
    db.add(user)
    db.flush()

    jeweller_id = None
    if payload.role == "jeweller":
        shop_code = f"GP-SHOP-{secrets.token_hex(3).upper()}"
        jp = JewellerProfile(
            user_id=user.id,
            shop_name=(payload.shop_name or f"{payload.full_name.strip()} Jewellers").strip(),
            shop_code=shop_code,
            city=payload.city or "Coimbatore",
            state=payload.state or "Tamil Nadu",
            valuation_conventions={
                "valuation_basis": "24K pure gold equivalent",
                "deductions_itemized": True,
            },
        )
        db.add(jp)
        db.flush()
        jeweller_id = jp.id

    record_audit_event(
        db=db,
        action="USER_REGISTERED",
        actor_user=user,
        jeweller_id=jeweller_id,
        details={"role": user.role, "email": user.email},
    )
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    return TokenResponse(access_token=token, user=_serialize_user(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user profile."""
    return _serialize_user(current_user)


@router.get("/demo-accounts", response_model=list[DemoAccountOut])
def list_demo_accounts():
    """List demo login credentials when DEMO_MODE is enabled."""
    if not get_settings().DEMO_MODE:
        return []
    return [DemoAccountOut(**item) for item in get_demo_accounts_catalog()]
