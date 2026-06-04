from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.middleware.auth import get_current_super_admin
from app.schemas.user import (
    CompanyCreateRequest, CompanyUpdateRequest,
    CompanyListResponse, CompanyResponse,
    PendingCompanyListResponse, CompanyRejectRequest, APIResponse,
)
from app.services.company_service import CompanyService

router = APIRouter(
    prefix="/admin/companies",
    tags=["Super Admin — Company Management"],
    dependencies=[Depends(get_current_super_admin)],
)


# ─── Standard CRUD ────────────────────────────────────────────────────────────

@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED,
             summary="Add a new approved company")
def create_company(payload: CompanyCreateRequest, db: Session = Depends(get_db)):
    return CompanyService.create_company(payload, db)


@router.get("/", response_model=CompanyListResponse, summary="List all approved companies")
def list_companies(
    page:      int            = Query(default=1,   ge=1),
    per_page:  int            = Query(default=20,  ge=1, le=100),
    search:    Optional[str]  = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    db:        Session        = Depends(get_db),
):
    return CompanyService.list_companies(db, page, per_page, search, is_active)


@router.get("/{company_id}", response_model=CompanyResponse, summary="Get company by ID")
def get_company(company_id: int, db: Session = Depends(get_db)):
    return CompanyService.get_company(company_id, db)


@router.patch("/{company_id}", response_model=CompanyResponse, summary="Update company details")
def update_company(company_id: int, payload: CompanyUpdateRequest, db: Session = Depends(get_db)):
    return CompanyService.update_company(company_id, payload, db)


@router.delete("/{company_id}", response_model=APIResponse, summary="Soft-delete a company")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    CompanyService.delete_company(company_id, db)
    return APIResponse(success=True, message="Company has been removed successfully.")


# ─── Pending Company Review ───────────────────────────────────────────────────

@router.get("/pending/list", response_model=PendingCompanyListResponse,
            summary="List all companies pending admin review")
def list_pending_companies(db: Session = Depends(get_db)):
    return CompanyService.list_pending_companies(db)


@router.patch("/{company_id}/approve", response_model=CompanyResponse,
              summary="Approve a pending company — auto-links waiting customer profiles")
def approve_company(company_id: int, db: Session = Depends(get_db)):
    return CompanyService.approve_company(company_id, db)


@router.patch("/{company_id}/reject", response_model=CompanyResponse,
              summary="Reject a pending company — marks waiting customer profiles as rejected")
def reject_company(
    company_id: int,
    payload: CompanyRejectRequest,
    db: Session = Depends(get_db),
):
    return CompanyService.reject_company(company_id, payload, db)
