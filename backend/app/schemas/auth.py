"""Authentication and user profile schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: Literal["jeweller", "customer"] = "customer"
    preferred_language: Literal["en", "ta"] = "en"
    shop_name: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default="Coimbatore", max_length=100)
    state: Optional[str] = Field(default="Tamil Nadu", max_length=100)


class JewellerProfileOut(BaseModel):
    id: str
    shop_name: str
    shop_code: str
    city: str
    state: str
    bis_hallmark_license: Optional[str] = None
    policy_max_deduction_pct: str
    policy_max_wastage_pct: str
    policy_max_fixed_deduction_inr: str
    policy_notes: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: str
    phone: Optional[str] = None
    full_name: str
    role: str
    preferred_language: str
    is_demo: bool
    jeweller_profile: Optional[JewellerProfileOut] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DemoAccountOut(BaseModel):
    label: str
    email: str
    password: str
    role: str
    preferred_language: str
    description: str
