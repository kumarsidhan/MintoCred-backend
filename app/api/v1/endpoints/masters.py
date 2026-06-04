from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.middleware.auth import get_current_super_admin
from app.schemas.user import MasterItemResponse, MasterCreateRequest, MasterUpdateRequest
from app.services.master_service import MasterService

router = APIRouter(prefix="/masters", tags=["Masters"])


# ─── Public read endpoints ────────────────────────────────────────────────────

@router.get("/genders", response_model=list[MasterItemResponse], summary="List genders")
def list_genders(db: Session = Depends(get_db)):
    return MasterService.get_genders(db)


@router.get("/employment-types", response_model=list[MasterItemResponse], summary="List employment types")
def list_employment_types(db: Session = Depends(get_db)):
    return MasterService.get_employment_types(db)


@router.get("/company-types", response_model=list[MasterItemResponse], summary="List company types")
def list_company_types(db: Session = Depends(get_db)):
    return MasterService.get_company_types(db)


@router.get("/company-industries", response_model=list[MasterItemResponse], summary="List company industries")
def list_company_industries(db: Session = Depends(get_db)):
    return MasterService.get_company_industries(db)


@router.get("/company-categories", response_model=list[MasterItemResponse], summary="List company categories")
def list_company_categories(db: Session = Depends(get_db)):
    return MasterService.get_company_categories(db)


# ─── Super Admin: Company Type CRUD ──────────────────────────────────────────

@router.post("/company-types", response_model=MasterItemResponse,
             summary="Add company type", dependencies=[Depends(get_current_super_admin)])
def create_company_type(payload: MasterCreateRequest, db: Session = Depends(get_db)):
    return MasterService.create_company_type(payload, db)


@router.patch("/company-types/{type_id}", response_model=MasterItemResponse,
              summary="Update company type", dependencies=[Depends(get_current_super_admin)])
def update_company_type(type_id: int, payload: MasterUpdateRequest, db: Session = Depends(get_db)):
    return MasterService.update_company_type(type_id, payload, db)


# ─── Super Admin: Company Industry CRUD ──────────────────────────────────────

@router.post("/company-industries", response_model=MasterItemResponse,
             summary="Add company industry", dependencies=[Depends(get_current_super_admin)])
def create_company_industry(payload: MasterCreateRequest, db: Session = Depends(get_db)):
    return MasterService.create_company_industry(payload, db)


@router.patch("/company-industries/{industry_id}", response_model=MasterItemResponse,
              summary="Update company industry", dependencies=[Depends(get_current_super_admin)])
def update_company_industry(industry_id: int, payload: MasterUpdateRequest, db: Session = Depends(get_db)):
    return MasterService.update_company_industry(industry_id, payload, db)


# ─── Super Admin: Company Category CRUD ──────────────────────────────────────

@router.post("/company-categories", response_model=MasterItemResponse,
             summary="Add company category", dependencies=[Depends(get_current_super_admin)])
def create_company_category(payload: MasterCreateRequest, db: Session = Depends(get_db)):
    return MasterService.create_company_category(payload, db)


@router.patch("/company-categories/{category_id}", response_model=MasterItemResponse,
              summary="Update company category", dependencies=[Depends(get_current_super_admin)])
def update_company_category(category_id: int, payload: MasterUpdateRequest, db: Session = Depends(get_db)):
    return MasterService.update_company_category(category_id, payload, db)
