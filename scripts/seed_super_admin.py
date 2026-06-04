"""
Seed script — creates the Super Admin account if it doesn't already exist.
Run once after first migration:  python -m scripts.seed_super_admin
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User, UserRole, UserStatus
from app.core.security import hash_password
from app.core.config import settings
from datetime import datetime, timezone


def seed_super_admin():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            User.email == settings.SUPER_ADMIN_EMAIL,
            User.role  == UserRole.SUPER_ADMIN,
        ).first()

        if existing:
            print(f"[SEED] Super Admin already exists: {settings.SUPER_ADMIN_EMAIL}")
            return

        admin = User(
            first_name=settings.SUPER_ADMIN_FIRST_NAME,
            last_name=settings.SUPER_ADMIN_LAST_NAME,
            email=settings.SUPER_ADMIN_EMAIL.lower(),
            mobile="0000000000",                       # placeholder
            hashed_password=hash_password(settings.SUPER_ADMIN_PASSWORD),
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()
        print(f"[SEED] Super Admin created successfully: {settings.SUPER_ADMIN_EMAIL}")
        print("[SEED] ⚠️  Change the default password immediately after first login!")

    except Exception as e:
        db.rollback()
        print(f"[SEED] ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_super_admin()
