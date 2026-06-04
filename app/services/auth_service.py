from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.models.user import User, UserRole, UserStatus, LoginLog
from app.schemas.user import CustomerRegisterRequest, LoginRequest, TokenResponse


class AuthService:

    # ─── Register ─────────────────────────────────────────────────────────────

    @staticmethod
    def register_customer(payload: CustomerRegisterRequest, db: Session) -> User:
        """
        Register a new customer.
        - OTP token is validated first — mobile must have been verified.
        - Checks for duplicate email/mobile before insert.
        - Passwords are bcrypt-hashed; plain-text is never persisted.
        """
        # ── Validate OTP token before anything else ────────────────────────
        from app.services.otp_service import OtpService
        OtpService.validate_otp_token(payload.otp_token, payload.mobile.strip())

        # Single query to check both email and mobile duplicates efficiently
        existing = (
            db.query(User.email, User.mobile)
            .filter(
                ((User.email == payload.email) | (User.mobile == payload.mobile)),
                User.is_deleted == False,
            )
            .first()
        )

        if existing:
            # Deliberately vague to prevent account enumeration
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email or mobile number already exists.",
            )

        user = User(
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip() if payload.last_name else None,
            email=payload.email.lower().strip(),
            mobile=payload.mobile.strip(),
            hashed_password=hash_password(payload.password),
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ─── Login ────────────────────────────────────────────────────────────────

    @staticmethod
    def login(
        payload: LoginRequest,
        db: Session,
        ip_address: str = "unknown",
        user_agent: str = "unknown",
    ) -> TokenResponse:
        """
        Authenticate user by email + password.
        - Always records login attempt in audit log (success or failure).
        - Generic error message prevents user enumeration.
        """
        user = (
            db.query(User)
            .filter(User.email == payload.email.lower().strip(), User.is_deleted == False)
            .first()
        )

        success = bool(user and verify_password(payload.password, user.hashed_password))

        # ── Audit log (always, regardless of outcome) ──────────────────────
        db.add(LoginLog(
            user_id=user.id if user else None,
            ip_address=ip_address[:45],
            user_agent=user_agent[:500],
            success=success,
        ))

        if not success:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if user.status == UserStatus.SUSPENDED:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been suspended. Please contact support.",
            )

        if user.status == UserStatus.INACTIVE:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is inactive. Please contact support.",
            )

        # ── Update last login timestamp ────────────────────────────────────
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

        access_token  = create_access_token(user.id, user.role.value)
        refresh_token = create_refresh_token(user.id, user.role.value)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
