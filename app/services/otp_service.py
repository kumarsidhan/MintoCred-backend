"""
OTP Service — handles sending and verifying OTPs.

Uses OtpLog table for persistence and the pluggable OTP provider for delivery.
OTP token (short-lived JWT) is issued after successful verification —
this token is required to complete registration.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.otp_provider import get_otp_provider, MockOTPProvider
from app.core.security import hash_password, verify_password
from app.models.user import OtpLog

# OTP validity window (minutes)
OTP_EXPIRE_MINUTES = 10


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _generate_otp() -> str:
    """
    Generate the OTP value.
    Currently returns the fixed mock value.
    When a real provider is active, switch to: secrets.randbelow(900000) + 100000
    """
    provider = get_otp_provider()
    if isinstance(provider, MockOTPProvider):
        return MockOTPProvider.FIXED_OTP

    import secrets
    return str(secrets.randbelow(900000) + 100000)   # 6-digit random


def _create_otp_token(mobile: str) -> str:
    """Issue a short-lived JWT proving OTP was verified for this mobile."""
    from datetime import timedelta
    from jose import jwt

    payload = {
        "sub": mobile,
        "type": "otp_verified",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_otp_token(token: str) -> dict | None:
    """Decode and validate the OTP token. Returns payload or None."""
    from jose import JWTError, jwt
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "otp_verified":
            return None
        return payload
    except JWTError:
        return None


# ─── OTP Service ─────────────────────────────────────────────────────────────

class OtpService:

    @staticmethod
    def send_otp(mobile: str, db: Session) -> None:
        """
        Generate OTP, save hashed copy to DB, send via provider.
        Invalidates any previous unused OTPs for this mobile.
        """
        from app.models.user import User

        # Invalidate all previous OTPs for this mobile
        db.query(OtpLog).filter(
            OtpLog.mobile == mobile,
            OtpLog.is_used == False,
        ).update({"is_used": True})

        otp = _generate_otp()
        hashed = hash_password(otp)   # bcrypt hash — never store plain OTP

        otp_log = OtpLog(
            mobile=mobile,
            otp_hash=hashed,
            is_used=False,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES),
        )
        db.add(otp_log)
        db.commit()

        # Send via provider (mock logs to console, real sends SMS)
        provider = get_otp_provider()
        sent = provider.send_otp(mobile, otp)

        if not sent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to send OTP. Please try again.",
            )

    @staticmethod
    def verify_otp(mobile: str, otp: str, db: Session) -> str:
        """
        Verify OTP for the given mobile.
        Returns a signed OTP token on success — required for registration.
        """
        otp_record = (
            db.query(OtpLog)
            .filter(
                OtpLog.mobile == mobile,
                OtpLog.is_used == False,
                OtpLog.expires_at > datetime.now(timezone.utc),
            )
            .order_by(OtpLog.created_at.desc())
            .first()
        )

        if not otp_record or not verify_password(otp, otp_record.otp_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP. Please request a new one.",
            )

        # Mark OTP as used
        otp_record.is_used = True
        db.commit()

        # Return signed token proving this mobile was verified
        return _create_otp_token(mobile)

    @staticmethod
    def validate_otp_token(otp_token: str, expected_mobile: str) -> None:
        """
        Called during registration to confirm OTP was verified
        for the exact mobile being registered.
        Raises 400 if token is invalid, expired, or mobile doesn't match.
        """
        payload = _decode_otp_token(otp_token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP verification token is invalid or expired. Please verify your mobile again.",
            )

        if payload.get("sub") != expected_mobile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP token does not match the mobile number provided.",
            )
