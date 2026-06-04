from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from fastapi import HTTPException, status

from app.models.user import (
    User, UserRole, UserStatus,
    CustomerProfile, Company, CompanyStatus, ProfileStatus,
    GenderMaster, EmploymentTypeMaster,
)
from app.schemas.user import (
    CustomerProfileUpdateRequest, CustomerProfileResponse,
    CustomerResponse, CustomerListResponse, AdminUpdateCustomerRequest,
)
from app.core.encryption import encrypt_pan, decrypt_pan, mask_pan


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _build_profile_response(profile: CustomerProfile) -> CustomerProfileResponse:
    pan_masked = None
    if profile.pan_encrypted:
        try:
            pan_masked = mask_pan(decrypt_pan(profile.pan_encrypted))
        except Exception:
            pass

    return CustomerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        gender_id=profile.gender_id,
        gender_label=profile.gender_master.label if profile.gender_master else None,
        dob=profile.dob,
        pincode=profile.pincode,
        address=profile.address,
        pan_masked=pan_masked,
        employment_type_id=profile.employment_type_id,
        employment_type_label=profile.employment_type_master.label if profile.employment_type_master else None,
        monthly_income=profile.monthly_income,
        company_id=profile.company_id,
        company_name=profile.company.name if profile.company else None,
        pending_company_id=profile.pending_company_id,
        pending_company_name=profile.pending_company.name if profile.pending_company else None,
        business_name=profile.business_name,
        profile_status=profile.profile_status,
        updated_at=profile.updated_at,
    )


def _build_customer_response(user: User) -> CustomerResponse:
    profile_resp = None
    if user.profile:
        profile_resp = _build_profile_response(user.profile)
    return CustomerResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        mobile=user.mobile,
        role=user.role,
        status=user.status,
        is_email_verified=user.is_email_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        profile=profile_resp,
    )


def _resolve_or_create_company(
    new_company_data,
    user_id: int,
    db: Session,
) -> tuple[Optional[int], Optional[int], ProfileStatus]:
    """
    Handles the 'Others' company flow.

    Returns (company_id, pending_company_id, profile_status):
      - If exact match found (approved): (company.id, None, APPROVED)
      - If already pending by anyone:    (None, company.id, PENDING)
      - If new:                          (None, new_company.id, PENDING)
    """
    name_lower = new_company_data.name.strip().lower()

    # Check for exact lowercase match
    existing = db.query(Company).filter(
        Company.name == name_lower,
        Company.is_deleted == False,
    ).first()

    if existing:
        if existing.status == CompanyStatus.APPROVED:
            # Link directly — no need for pending
            return existing.id, None, ProfileStatus.APPROVED
        else:
            # Company exists but still pending/rejected — link to it as pending
            return None, existing.id, ProfileStatus.PENDING

    # No match — create new pending company
    company = Company(
        name=name_lower,
        address=new_company_data.address,
        office_phone=new_company_data.office_phone,
        office_email=new_company_data.office_email,
        type_id=new_company_data.type_id,
        industry_id=new_company_data.industry_id,
        category_id=new_company_data.category_id,
        status=CompanyStatus.PENDING,
        submitted_by_user_id=user_id,
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(company)
    db.flush()   # get company.id before commit
    return None, company.id, ProfileStatus.PENDING


class CustomerService:

    # ─── Profile Update (by customer themselves) ──────────────────────────────

    @staticmethod
    def update_profile(
        user_id: int,
        payload: CustomerProfileUpdateRequest,
        db: Session,
    ) -> CustomerProfileResponse:
        """
        Customer updates their own extended profile.

        Company selection logic:
          - company_id provided   → link to existing approved company directly
          - new_company provided  → 'Others' flow: check duplicate, create pending if new
          - Neither provided      → no company change
        """
        # ── Validate gender ───────────────────────────────────────────────────
        if payload.gender_id:
            gender = db.query(GenderMaster).filter(
                GenderMaster.id == payload.gender_id,
                GenderMaster.is_active == True,
            ).first()
            if not gender:
                raise HTTPException(status_code=400, detail="Invalid gender selected.")

        # ── Validate employment type ──────────────────────────────────────────
        emp_type = None
        if payload.employment_type_id:
            emp_type = db.query(EmploymentTypeMaster).filter(
                EmploymentTypeMaster.id == payload.employment_type_id,
                EmploymentTypeMaster.is_active == True,
            ).first()
            if not emp_type:
                raise HTTPException(status_code=400, detail="Invalid employment type selected.")

        # ── Employment-specific rules ─────────────────────────────────────────
        if emp_type:
            if emp_type.code == "SALARIED":
                if payload.business_name:
                    raise HTTPException(status_code=400,
                        detail="Business name is only for self-employed customers.")
                # Validate existing company_id if provided
                if payload.company_id:
                    company = db.query(Company).filter(
                        Company.id == payload.company_id,
                        Company.status == CompanyStatus.APPROVED,
                        Company.is_active == True,
                        Company.is_deleted == False,
                    ).first()
                    if not company:
                        raise HTTPException(status_code=400,
                            detail="Selected company not found or not yet approved.")

            elif emp_type.code == "SELF_EMPLOYED":
                if payload.company_id or payload.new_company:
                    raise HTTPException(status_code=400,
                        detail="Company selection is only for salaried customers.")

        # ── PAN uniqueness check ──────────────────────────────────────────────
        if payload.pan_number:
            other_pans = db.query(
                CustomerProfile.pan_encrypted, CustomerProfile.user_id
            ).filter(
                CustomerProfile.pan_encrypted.isnot(None),
                CustomerProfile.user_id != user_id,
            ).all()
            for row in other_pans:
                try:
                    if decrypt_pan(row.pan_encrypted) == payload.pan_number.upper():
                        raise HTTPException(status_code=409,
                            detail="This PAN number is already linked to another account.")
                except HTTPException:
                    raise
                except Exception:
                    continue

        # ── Get or create profile ─────────────────────────────────────────────
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.user_id == user_id
        ).first()

        if not profile:
            profile = CustomerProfile(
                user_id=user_id,
                profile_status=ProfileStatus.INCOMPLETE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(profile)

        # ── Apply scalar fields ───────────────────────────────────────────────
        update_data = payload.model_dump(exclude_unset=True, exclude={"pan_number", "new_company"})

        # Remove company_id from update_data — handled separately below
        update_data.pop("company_id", None)

        for field, value in update_data.items():
            setattr(profile, field, value)

        if payload.pan_number:
            profile.pan_encrypted = encrypt_pan(payload.pan_number)

        # ── Company logic ─────────────────────────────────────────────────────
        if payload.company_id:
            # Existing approved company — link directly
            profile.company_id         = payload.company_id
            profile.pending_company_id = None
            profile.profile_status     = ProfileStatus.APPROVED

        elif payload.new_company:
            # 'Others' flow
            company_id, pending_id, prof_status = _resolve_or_create_company(
                payload.new_company, user_id, db
            )
            profile.company_id         = company_id
            profile.pending_company_id = pending_id
            profile.profile_status     = prof_status

        elif profile.profile_status == ProfileStatus.INCOMPLETE and profile.company_id:
            # Already linked — keep status
            profile.profile_status = ProfileStatus.APPROVED

        profile.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(profile)

        # Eagerly load relationships
        if profile.gender_id:
            _ = profile.gender_master
        if profile.employment_type_id:
            _ = profile.employment_type_master
        if profile.company_id:
            _ = profile.company
        if profile.pending_company_id:
            _ = profile.pending_company

        return _build_profile_response(profile)

    # ─── List Customers ───────────────────────────────────────────────────────

    @staticmethod
    def list_customers(
        db: Session,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[UserStatus] = None,
    ) -> CustomerListResponse:
        query = (
            db.query(User)
            .options(
                joinedload(User.profile).joinedload(CustomerProfile.gender_master),
                joinedload(User.profile).joinedload(CustomerProfile.employment_type_master),
                joinedload(User.profile).joinedload(CustomerProfile.company),
                joinedload(User.profile).joinedload(CustomerProfile.pending_company),
            )
            .filter(User.role == UserRole.CUSTOMER, User.is_deleted == False)
        )

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(or_(
                User.first_name.ilike(term),
                User.last_name.ilike(term),
                User.email.ilike(term),
                User.mobile.ilike(term),
            ))

        if status_filter:
            query = query.filter(User.status == status_filter)

        total     = query.count()
        customers = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

        return CustomerListResponse(
            total=total, page=page, per_page=per_page,
            data=[_build_customer_response(c) for c in customers],
        )

    # ─── Get Single Customer ──────────────────────────────────────────────────

    @staticmethod
    def get_customer(customer_id: int, db: Session) -> CustomerResponse:
        user = (
            db.query(User)
            .options(
                joinedload(User.profile).joinedload(CustomerProfile.gender_master),
                joinedload(User.profile).joinedload(CustomerProfile.employment_type_master),
                joinedload(User.profile).joinedload(CustomerProfile.company),
                joinedload(User.profile).joinedload(CustomerProfile.pending_company),
            )
            .filter(User.id == customer_id, User.role == UserRole.CUSTOMER, User.is_deleted == False)
            .first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="Customer not found.")
        return _build_customer_response(user)

    # ─── Admin Update Customer ────────────────────────────────────────────────

    @staticmethod
    def admin_update_customer(
        customer_id: int,
        payload: AdminUpdateCustomerRequest,
        db: Session,
    ) -> CustomerResponse:
        user = db.query(User).filter(
            User.id == customer_id, User.role == UserRole.CUSTOMER, User.is_deleted == False
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="Customer not found.")

        if payload.mobile and payload.mobile != user.mobile:
            taken = db.query(User.id).filter(
                User.mobile == payload.mobile, User.is_deleted == False
            ).first()
            if taken:
                raise HTTPException(status_code=409,
                    detail="Mobile number already linked to another account.")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        return CustomerService.get_customer(customer_id, db)

    # ─── Soft Delete ──────────────────────────────────────────────────────────

    @staticmethod
    def delete_customer(customer_id: int, db: Session) -> None:
        user = db.query(User).filter(
            User.id == customer_id, User.role == UserRole.CUSTOMER, User.is_deleted == False
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="Customer not found.")
        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        user.status     = UserStatus.INACTIVE
        db.commit()
