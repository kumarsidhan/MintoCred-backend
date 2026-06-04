import re
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator, ConfigDict

from app.models.user import UserRole, UserStatus, CompanyStatus, ProfileStatus

# ─── Shared Validators ────────────────────────────────────────────────────────

MOBILE_REGEX   = re.compile(r"^[6-9]\d{9}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^])[A-Za-z\d@$!%*?&#^]{8,64}$")
PAN_REGEX      = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
PINCODE_REGEX  = re.compile(r"^\d{6}$")
PHONE_REGEX    = re.compile(r"^\+?[\d\s\-]{7,20}$")
EMAIL_REGEX    = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def validate_mobile(v: str) -> str:
    if not MOBILE_REGEX.match(v):
        raise ValueError("Enter a valid 10-digit Indian mobile number starting with 6–9.")
    return v

def validate_password_strength(v: str) -> str:
    if not PASSWORD_REGEX.match(v):
        raise ValueError(
            "Password must be 8–64 characters with at least one uppercase, "
            "one lowercase, one digit, and one special character (@$!%*?&#^)."
        )
    return v

99
# ─── Registration ─────────────────────────────────────────────────────────────

class CustomerRegisterRequest(BaseModel):
    first_name:       str
    last_name:        Optional[str] = None
    email:            EmailStr
    mobile:           str
    password:         str
    confirm_password: str
    otp_token:        str

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        v = v.strip()
        if not (2 <= len(v) <= 100):
            raise ValueError("First name must be 2–100 characters.")
        if not re.match(r"^[A-Za-z\s'-]+$", v):
            raise ValueError("First name may only contain letters, spaces, hyphens, or apostrophes.")
        return v

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip()
            if not re.match(r"^[A-Za-z\s'-]+$", v):
                raise ValueError("Last name may only contain letters, spaces, hyphens, or apostrophes.")
        return v

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v: str) -> str:
        return validate_mobile(v.strip())

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_must_match(self) -> "CustomerRegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Password and confirm password do not match.")
        return self


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int


# ─── OTP Schemas ──────────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    mobile: str

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v: str) -> str:
        return validate_mobile(v.strip())


class VerifyOTPRequest(BaseModel):
    mobile: str
    otp:    str

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v: str) -> str:
        return validate_mobile(v.strip())

    @field_validator("otp")
    @classmethod
    def check_otp(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or not (4 <= len(v) <= 6):
            raise ValueError("OTP must be 4–6 digits.")
        return v


class OTPVerifyResponse(BaseModel):
    success:   bool
    message:   str
    otp_token: str


# ─── Company Suggest (embedded in profile update) ─────────────────────────────

class CompanySuggestRequest(BaseModel):
    """
    Sent by customer when they select 'Others'.
    All fields except name are optional — admin can complete later.
    """
    name:         str
    address:      Optional[str] = None
    office_phone: Optional[str] = None
    office_email: Optional[str] = None
    type_id:      Optional[int] = None
    industry_id:  Optional[int] = None
    category_id:  Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip().lower()          # always lowercase
        if not (2 <= len(v) <= 255):
            raise ValueError("Company name must be 2–255 characters.")
        return v

    @field_validator("office_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not PHONE_REGEX.match(v.strip()):
            raise ValueError("Enter a valid office phone number.")
        return v.strip() if v else v

    @field_validator("office_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not EMAIL_REGEX.match(v.strip()):
            raise ValueError("Enter a valid office email address.")
        return v.strip().lower() if v else v


# ─── Customer Profile Update ──────────────────────────────────────────────────

class CustomerProfileUpdateRequest(BaseModel):
    gender_id:          Optional[int]     = None
    dob:                Optional[date]    = None
    pincode:            Optional[str]     = None
    address:            Optional[str]     = None
    pan_number:         Optional[str]     = None
    employment_type_id: Optional[int]     = None
    monthly_income:     Optional[Decimal] = None
    # Salaried — pick existing company
    company_id:         Optional[int]     = None
    # Salaried — suggest new company (Others option)
    new_company:        Optional[CompanySuggestRequest] = None
    # Self-employed
    business_name:      Optional[str]     = None

    @field_validator("company_id")
    @classmethod
    def check_company_id(cls, v: Optional[int]) -> Optional[int]:
        if v == 0:
            return None
        return v

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if not PAN_REGEX.match(v):
                raise ValueError("Invalid PAN format. Expected: ABCDE1234F")
        return v

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: Optional[str]) -> Optional[str]:
        if v and not PINCODE_REGEX.match(v.strip()):
            raise ValueError("Pincode must be exactly 6 digits.")
        return v

    @field_validator("dob")
    @classmethod
    def validate_dob(cls, v: Optional[date]) -> Optional[date]:
        if v:
            from datetime import date as dt
            today = dt.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 18:
                raise ValueError("Customer must be at least 18 years old.")
            if age > 100:
                raise ValueError("Please enter a valid date of birth.")
        return v

    @field_validator("monthly_income")
    @classmethod
    def validate_income(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Monthly income must be greater than 0.")
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v.strip()) > 500:
            raise ValueError("Address must not exceed 500 characters.")
        return v.strip() if v else v

    @model_validator(mode="after")
    def validate_company_fields(self) -> "CustomerProfileUpdateRequest":
        if self.company_id and self.new_company:
            raise ValueError("Provide either company_id or new_company, not both.")
        return self


# ─── Profile Response ─────────────────────────────────────────────────────────

class CompanyBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:     int
    name:   str
    status: CompanyStatus


class CustomerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    int
    user_id:               int
    gender_id:             Optional[int]
    gender_label:          Optional[str]    = None
    dob:                   Optional[date]
    pincode:               Optional[str]
    address:               Optional[str]
    pan_masked:            Optional[str]    = None
    employment_type_id:    Optional[int]
    employment_type_label: Optional[str]    = None
    monthly_income:        Optional[Decimal]
    company_id:            Optional[int]
    company_name:          Optional[str]    = None
    pending_company_id:    Optional[int]    = None
    pending_company_name:  Optional[str]    = None
    business_name:         Optional[str]
    profile_status:        ProfileStatus
    updated_at:            datetime


# ─── Customer Full Response ───────────────────────────────────────────────────

class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    first_name:       str
    last_name:        Optional[str]
    email:            str
    mobile:           str
    role:             UserRole
    status:           UserStatus
    is_email_verified: bool
    created_at:       datetime
    updated_at:       datetime
    last_login_at:    Optional[datetime]
    profile:          Optional[CustomerProfileResponse] = None


class CustomerListResponse(BaseModel):
    total:    int
    page:     int
    per_page: int
    data:     list[CustomerResponse]


# ─── Admin Update Customer ────────────────────────────────────────────────────

class AdminUpdateCustomerRequest(BaseModel):
    first_name: Optional[str]        = None
    last_name:  Optional[str]        = None
    mobile:     Optional[str]        = None
    status:     Optional[UserStatus] = None

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip()
            if not (2 <= len(v) <= 100):
                raise ValueError("First name must be 2–100 characters.")
        return v

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_mobile(v.strip())
        return v


# ─── Master Schemas ───────────────────────────────────────────────────────────

class MasterItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:        int
    code:      str
    label:     str
    is_active: bool


class MasterCreateRequest(BaseModel):
    code:  str
    label: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not (2 <= len(v) <= 50):
            raise ValueError("Code must be 2–50 characters.")
        return v

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        v = v.strip()
        if not (2 <= len(v) <= 100):
            raise ValueError("Label must be 2–100 characters.")
        return v


class MasterUpdateRequest(BaseModel):
    label:     Optional[str]  = None
    is_active: Optional[bool] = None


# ─── Company Schemas ──────────────────────────────────────────────────────────

class CompanyCreateRequest(BaseModel):
    name:         str
    address:      Optional[str] = None
    office_phone: Optional[str] = None
    office_email: Optional[str] = None
    type_id:      Optional[int] = None
    industry_id:  Optional[int] = None
    category_id:  Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip().lower()          # always lowercase
        if not (2 <= len(v) <= 255):
            raise ValueError("Company name must be 2–255 characters.")
        return v


class CompanyUpdateRequest(BaseModel):
    name:         Optional[str]  = None
    address:      Optional[str]  = None
    office_phone: Optional[str]  = None
    office_email: Optional[str]  = None
    type_id:      Optional[int]  = None
    industry_id:  Optional[int]  = None
    category_id:  Optional[int]  = None
    is_active:    Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().lower()
            if not (2 <= len(v) <= 255):
                raise ValueError("Company name must be 2–255 characters.")
        return v


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           int
    name:         str
    address:      Optional[str]
    office_phone: Optional[str]
    office_email: Optional[str]
    type_id:      Optional[int]
    industry_id:  Optional[int]
    category_id:  Optional[int]
    status:       CompanyStatus
    is_active:    bool
    created_at:   datetime
    updated_at:   datetime


class CompanyListResponse(BaseModel):
    total:    int
    page:     int
    per_page: int
    data:     list[CompanyResponse]


class PendingCompanyListResponse(BaseModel):
    total: int
    data:  list[CompanyResponse]


class CompanyRejectRequest(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Rejection reason cannot be empty.")
        return v


# ─── Generic Response ─────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool
    message: str
    data:    Optional[dict | list] = None
