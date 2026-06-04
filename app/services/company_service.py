from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import (
    Company, CompanyStatus, CustomerProfile, ProfileStatus
)
from app.schemas.user import (
    CompanyCreateRequest, CompanyUpdateRequest,
    CompanyListResponse, CompanyResponse,
    PendingCompanyListResponse, CompanyRejectRequest,
)


class CompanyService:

    # ─── Admin: Create (always approved) ─────────────────────────────────────

    @staticmethod
    def create_company(payload: CompanyCreateRequest, db: Session) -> Company:
        name = payload.name.strip().lower()   # always lowercase

        existing = db.query(Company).filter(
            Company.name == name,
            Company.is_deleted == False,
        ).first()
        if existing:
            raise HTTPException(status_code=409,
                detail="A company with this name already exists.")

        company = Company(
            name=name,
            address=payload.address,
            office_phone=payload.office_phone,
            office_email=payload.office_email,
            type_id=payload.type_id,
            industry_id=payload.industry_id,
            category_id=payload.category_id,
            status=CompanyStatus.APPROVED,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        return company

    # ─── List approved companies ──────────────────────────────────────────────

    @staticmethod
    def list_companies(
        db: Session,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> CompanyListResponse:
        query = db.query(Company).filter(
            Company.is_deleted == False,
            Company.status == CompanyStatus.APPROVED,
        )
        if search:
            query = query.filter(Company.name.ilike(f"%{search.strip().lower()}%"))
        if is_active is not None:
            query = query.filter(Company.is_active == is_active)

        total     = query.count()
        companies = query.order_by(Company.name.asc()).offset((page - 1) * per_page).limit(per_page).all()
        return CompanyListResponse(
            total=total, page=page, per_page=per_page,
            data=[CompanyResponse.model_validate(c) for c in companies],
        )

    # ─── Get single ───────────────────────────────────────────────────────────

    @staticmethod
    def get_company(company_id: int, db: Session) -> Company:
        company = db.query(Company).filter(
            Company.id == company_id,
            Company.is_deleted == False,
        ).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")
        return company

    # ─── Update ───────────────────────────────────────────────────────────────

    @staticmethod
    def update_company(company_id: int, payload: CompanyUpdateRequest, db: Session) -> Company:
        company = CompanyService.get_company(company_id, db)

        if payload.name:
            new_name = payload.name.strip().lower()
            if new_name != company.name:
                duplicate = db.query(Company).filter(
                    Company.name == new_name,
                    Company.is_deleted == False,
                    Company.id != company_id,
                ).first()
                if duplicate:
                    raise HTTPException(status_code=409,
                        detail="A company with this name already exists.")
            payload_dict = payload.model_dump(exclude_unset=True)
            payload_dict["name"] = new_name
            for field, value in payload_dict.items():
                setattr(company, field, value)
        else:
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(company, field, value)

        company.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(company)
        return company

    # ─── Soft delete ──────────────────────────────────────────────────────────

    @staticmethod
    def delete_company(company_id: int, db: Session) -> None:
        company = CompanyService.get_company(company_id, db)
        company.is_deleted = True
        company.is_active  = False
        company.deleted_at = datetime.now(timezone.utc)
        db.commit()

    # ─── List pending companies ───────────────────────────────────────────────

    @staticmethod
    def list_pending_companies(db: Session) -> PendingCompanyListResponse:
        companies = db.query(Company).filter(
            Company.status == CompanyStatus.PENDING,
            Company.is_deleted == False,
        ).order_by(Company.created_at.asc()).all()

        return PendingCompanyListResponse(
            total=len(companies),
            data=[CompanyResponse.model_validate(c) for c in companies],
        )

    # ─── Approve company ──────────────────────────────────────────────────────

    @staticmethod
    def approve_company(company_id: int, db: Session) -> CompanyResponse:
        company = CompanyService.get_company(company_id, db)

        if company.status != CompanyStatus.PENDING:
            raise HTTPException(status_code=400,
                detail=f"Company is already {company.status.value}.")

        # Approve the company
        company.status    = CompanyStatus.APPROVED
        company.is_active = True
        company.updated_at = datetime.now(timezone.utc)

        # Auto-link all profiles that were waiting on this company
        waiting_profiles = db.query(CustomerProfile).filter(
            CustomerProfile.pending_company_id == company_id,
        ).all()

        for profile in waiting_profiles:
            profile.company_id         = company_id
            profile.pending_company_id = None
            profile.profile_status     = ProfileStatus.APPROVED
            profile.updated_at         = datetime.now(timezone.utc)

        db.commit()
        db.refresh(company)
        return CompanyResponse.model_validate(company)

    # ─── Reject company ───────────────────────────────────────────────────────

    @staticmethod
    def reject_company(company_id: int, payload: CompanyRejectRequest, db: Session) -> CompanyResponse:
        company = CompanyService.get_company(company_id, db)

        if company.status != CompanyStatus.PENDING:
            raise HTTPException(status_code=400,
                detail=f"Company is already {company.status.value}.")

        # Reject the company
        company.status           = CompanyStatus.REJECTED
        company.rejection_reason = payload.reason
        company.is_active        = False
        company.updated_at       = datetime.now(timezone.utc)

        # Reject all profiles that were waiting on this company
        waiting_profiles = db.query(CustomerProfile).filter(
            CustomerProfile.pending_company_id == company_id,
        ).all()

        for profile in waiting_profiles:
            profile.profile_status = ProfileStatus.REJECTED
            profile.updated_at     = datetime.now(timezone.utc)
            # Keep pending_company_id so customer knows which company was rejected

        db.commit()
        db.refresh(company)
        return CompanyResponse.model_validate(company)
