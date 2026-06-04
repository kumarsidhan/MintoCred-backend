from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Numeric,
    Enum as SAEnum, Index, ForeignKey, Text
)
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base


# ─── Enums ───────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN       = "admin"
    CUSTOMER    = "customer"


class UserStatus(str, enum.Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"


class CompanyStatus(str, enum.Enum):
    PENDING  = "pending"    # submitted by customer, awaiting admin review
    APPROVED = "approved"   # admin approved
    REJECTED = "rejected"   # admin rejected


class ProfileStatus(str, enum.Enum):
    INCOMPLETE = "incomplete"  # profile not yet filled
    PENDING    = "pending"     # company under review
    APPROVED   = "approved"    # company approved
    REJECTED   = "rejected"    # company rejected — can resubmit


# ─── Master Models ────────────────────────────────────────────────────────────

class GenderMaster(Base):
    __tablename__ = "master_gender"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    code       = Column(String(20),  nullable=False, unique=True)
    label      = Column(String(50),  nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    customers  = relationship("CustomerProfile", back_populates="gender_master")

    __table_args__ = (Index("ix_master_gender_code", "code"),)


class EmploymentTypeMaster(Base):
    __tablename__ = "master_employment_type"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    code       = Column(String(30),  nullable=False, unique=True)
    label      = Column(String(100), nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    customers  = relationship("CustomerProfile", back_populates="employment_type_master")

    __table_args__ = (Index("ix_master_employment_code", "code"),)


class CompanyTypeMaster(Base):
    """e.g. Private Ltd, Public Ltd, Partnership, Proprietorship"""
    __tablename__ = "master_company_type"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    code       = Column(String(50),  nullable=False, unique=True)
    label      = Column(String(100), nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    companies  = relationship("Company", back_populates="company_type")

    __table_args__ = (Index("ix_master_company_type_code", "code"),)


class CompanyIndustryMaster(Base):
    """e.g. IT, Finance, Manufacturing, Healthcare"""
    __tablename__ = "master_company_industry"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    code       = Column(String(50),  nullable=False, unique=True)
    label      = Column(String(100), nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    companies  = relationship("Company", back_populates="industry")

    __table_args__ = (Index("ix_master_company_industry_code", "code"),)


class CompanyCategoryMaster(Base):
    """e.g. CAT-A, CAT-B, CAT-C — used for lender matching"""
    __tablename__ = "master_company_category"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    code       = Column(String(50),  nullable=False, unique=True)
    label      = Column(String(100), nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    companies  = relationship("Company", back_populates="category")

    __table_args__ = (Index("ix_master_company_category_code", "code"),)


class Company(Base):
    """
    Master list of companies.
    - Admin-added companies: status=approved, submitted_by_user_id=NULL
    - Customer-suggested companies: status=pending, submitted_by_user_id=<user_id>
    - Company name always stored in lowercase for exact matching.
    """
    __tablename__ = "companies"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    name                = Column(String(255), nullable=False, unique=True)   # always lowercase
    address             = Column(Text,        nullable=True)
    office_phone        = Column(String(20),  nullable=True)
    office_email        = Column(String(255), nullable=True)

    # FKs to new master tables
    type_id             = Column(Integer, ForeignKey("master_company_type.id"),     nullable=True)
    industry_id         = Column(Integer, ForeignKey("master_company_industry.id"), nullable=True)
    category_id         = Column(Integer, ForeignKey("master_company_category.id"), nullable=True)

    # Status & review
    status              = Column(SAEnum(CompanyStatus), nullable=False, default=CompanyStatus.APPROVED)
    rejection_reason    = Column(String(500), nullable=True)
    submitted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    is_deleted  = Column(Boolean, default=False, nullable=False)
    deleted_at  = Column(DateTime, nullable=True)

    # Relationships
    customers        = relationship("CustomerProfile", back_populates="company",
                                    foreign_keys="CustomerProfile.company_id")
    company_type     = relationship("CompanyTypeMaster",     back_populates="companies")
    industry         = relationship("CompanyIndustryMaster", back_populates="companies")
    category         = relationship("CompanyCategoryMaster", back_populates="companies")
    submitted_by     = relationship("User", foreign_keys=[submitted_by_user_id])

    __table_args__ = (
        Index("ix_companies_name",       "name"),
        Index("ix_companies_status",     "status"),
        Index("ix_companies_is_deleted", "is_deleted"),
    )


# ─── User Model ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    first_name       = Column(String(100), nullable=False)
    last_name        = Column(String(100), nullable=True)
    email            = Column(String(255), nullable=False, unique=True)
    mobile           = Column(String(15),  nullable=False, unique=True)
    hashed_password  = Column(String(255), nullable=False)
    role             = Column(SAEnum(UserRole),   nullable=False, default=UserRole.CUSTOMER)
    status           = Column(SAEnum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    is_email_verified = Column(Boolean, default=False, nullable=False)

    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at  = Column(DateTime, nullable=True)
    is_deleted     = Column(Boolean, default=False, nullable=False)
    deleted_at     = Column(DateTime, nullable=True)

    profile    = relationship("CustomerProfile", back_populates="user", uselist=False)
    login_logs = relationship("LoginLog", back_populates="user", lazy="dynamic")

    __table_args__ = (
        Index("ix_users_email",       "email"),
        Index("ix_users_mobile",      "mobile"),
        Index("ix_users_role_status", "role", "status"),
        Index("ix_users_is_deleted",  "is_deleted"),
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"


# ─── Customer Profile ─────────────────────────────────────────────────────────

class CustomerProfile(Base):
    """
    Extended profile for customers — collected after registration.
    One-to-one with User. PAN is AES-encrypted before storage.

    profile_status:
      INCOMPLETE — not yet submitted
      PENDING    — company suggested by customer, awaiting admin approval
      APPROVED   — company approved, profile complete
      REJECTED   — company rejected by admin, customer can resubmit
    """
    __tablename__ = "customer_profiles"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    user_id              = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"),
                                  nullable=False, unique=True)

    # Personal
    gender_id            = Column(Integer, ForeignKey("master_gender.id"), nullable=True)
    dob                  = Column(Date,         nullable=True)
    pincode              = Column(String(10),   nullable=True)
    address              = Column(String(500),  nullable=True)
    pan_encrypted        = Column(String(500),  nullable=True)

    # Employment
    employment_type_id   = Column(Integer, ForeignKey("master_employment_type.id"), nullable=True)
    monthly_income       = Column(Numeric(12, 2), nullable=True)

    # Salaried → approved company FK (NULL while pending)
    company_id           = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # Pending company — set while company awaits approval
    pending_company_id   = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # Self-employed → free text
    business_name        = Column(String(255), nullable=True)

    # Profile review status
    profile_status       = Column(SAEnum(ProfileStatus), nullable=False,
                                  default=ProfileStatus.INCOMPLETE)

    # Audit
    created_at           = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at           = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                                  onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user                   = relationship("User", back_populates="profile")
    gender_master          = relationship("GenderMaster", back_populates="customers")
    employment_type_master = relationship("EmploymentTypeMaster", back_populates="customers")
    company                = relationship("Company", back_populates="customers",
                                          foreign_keys=[company_id])
    pending_company        = relationship("Company", foreign_keys=[pending_company_id])

    __table_args__ = (
        Index("ix_customer_profiles_user_id",        "user_id"),
        Index("ix_customer_profiles_profile_status", "profile_status"),
    )


# ─── OTP Log ─────────────────────────────────────────────────────────────────

class OtpLog(Base):
    __tablename__ = "otp_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    mobile     = Column(String(15),  nullable=False)
    otp_hash   = Column(String(255), nullable=False)
    is_used    = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_otp_logs_mobile",     "mobile"),
        Index("ix_otp_logs_expires_at", "expires_at"),
    )


# ─── Login Audit Log ─────────────────────────────────────────────────────────

class LoginLog(Base):
    __tablename__ = "login_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    ip_address = Column(String(45),  nullable=True)
    user_agent = Column(String(500), nullable=True)
    success    = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="login_logs")

    __table_args__ = (
        Index("ix_login_logs_user_id",    "user_id"),
        Index("ix_login_logs_created_at", "created_at"),
    )
