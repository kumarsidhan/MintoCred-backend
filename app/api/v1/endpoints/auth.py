from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import (
    CustomerRegisterRequest, LoginRequest, TokenResponse,
    CustomerResponse, APIResponse,
    SendOTPRequest, VerifyOTPRequest, OTPVerifyResponse,
)
from app.services.auth_service import AuthService
from app.services.otp_service import OtpService
from app.middleware.auth import get_client_ip

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─── Send OTP ─────────────────────────────────────────────────────────────────

@router.post(
    "/send-otp",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Send OTP to mobile",
    description=(
        "Step 1 of registration. Sends a 4–6 digit OTP to the given mobile number. "
        "OTP is valid for 10 minutes. During development the OTP is always 1234."
    ),
)
def send_otp(
    payload: SendOTPRequest,
    db: Session = Depends(get_db),
):
    OtpService.send_otp(payload.mobile, db)
    return APIResponse(
        success=True,
        message="OTP sent successfully. Please enter the OTP to verify your mobile.",
    )


# ─── Verify OTP ───────────────────────────────────────────────────────────────

@router.post(
    "/verify-otp",
    response_model=OTPVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP",
    description=(
        "Step 2 of registration. Verifies the OTP entered by the user. "
        "Returns a short-lived otp_token — pass this in /register to complete registration."
    ),
)
def verify_otp(
    payload: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    otp_token = OtpService.verify_otp(payload.mobile, payload.otp, db)
    return OTPVerifyResponse(
        success=True,
        message="Mobile verified successfully. You can now complete registration.",
        otp_token=otp_token,
    )


# ─── Register ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Customer Registration",
    description=(
        "Step 3 of registration. Requires a valid otp_token from /verify-otp. "
        "Password is bcrypt-hashed before storage."
    ),
)
def register(
    payload: CustomerRegisterRequest,
    db: Session = Depends(get_db),
):
    user = AuthService.register_customer(payload, db)
    return APIResponse(
        success=True,
        message="Account created successfully. Please verify your email to continue.",
        data=CustomerResponse.model_validate(user).model_dump(),
    )


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Customer / Admin Login",
    description="Login with email and password. Returns JWT access + refresh tokens.",
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip    = get_client_ip(request)
    agent = request.headers.get("User-Agent", "unknown")
    return AuthService.login(payload, db, ip_address=ip, user_agent=agent)

