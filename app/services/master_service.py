from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import (
    GenderMaster, EmploymentTypeMaster,
    CompanyTypeMaster, CompanyIndustryMaster, CompanyCategoryMaster,
)
from app.schemas.user import MasterCreateRequest, MasterUpdateRequest


class MasterService:

    # ─── Gender ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_genders(db: Session):
        return db.query(GenderMaster).filter(GenderMaster.is_active == True).order_by(GenderMaster.id).all()

    # ─── Employment Type ──────────────────────────────────────────────────────

    @staticmethod
    def get_employment_types(db: Session):
        return db.query(EmploymentTypeMaster).filter(
            EmploymentTypeMaster.is_active == True
        ).order_by(EmploymentTypeMaster.id).all()

    # ─── Company Type ─────────────────────────────────────────────────────────

    @staticmethod
    def get_company_types(db: Session):
        return db.query(CompanyTypeMaster).filter(
            CompanyTypeMaster.is_active == True
        ).order_by(CompanyTypeMaster.id).all()

    @staticmethod
    def create_company_type(payload: MasterCreateRequest, db: Session) -> CompanyTypeMaster:
        existing = db.query(CompanyTypeMaster).filter(
            CompanyTypeMaster.code == payload.code
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Company type with this code already exists.")
        item = CompanyTypeMaster(code=payload.code, label=payload.label)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_company_type(type_id: int, payload: MasterUpdateRequest, db: Session) -> CompanyTypeMaster:
        item = db.query(CompanyTypeMaster).filter(CompanyTypeMaster.id == type_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Company type not found.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        return item

    # ─── Company Industry ─────────────────────────────────────────────────────

    @staticmethod
    def get_company_industries(db: Session):
        return db.query(CompanyIndustryMaster).filter(
            CompanyIndustryMaster.is_active == True
        ).order_by(CompanyIndustryMaster.id).all()

    @staticmethod
    def create_company_industry(payload: MasterCreateRequest, db: Session) -> CompanyIndustryMaster:
        existing = db.query(CompanyIndustryMaster).filter(
            CompanyIndustryMaster.code == payload.code
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Industry with this code already exists.")
        item = CompanyIndustryMaster(code=payload.code, label=payload.label)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_company_industry(industry_id: int, payload: MasterUpdateRequest, db: Session) -> CompanyIndustryMaster:
        item = db.query(CompanyIndustryMaster).filter(CompanyIndustryMaster.id == industry_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Industry not found.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        return item

    # ─── Company Category ─────────────────────────────────────────────────────

    @staticmethod
    def get_company_categories(db: Session):
        return db.query(CompanyCategoryMaster).filter(
            CompanyCategoryMaster.is_active == True
        ).order_by(CompanyCategoryMaster.id).all()

    @staticmethod
    def create_company_category(payload: MasterCreateRequest, db: Session) -> CompanyCategoryMaster:
        existing = db.query(CompanyCategoryMaster).filter(
            CompanyCategoryMaster.code == payload.code
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Category with this code already exists.")
        item = CompanyCategoryMaster(code=payload.code, label=payload.label)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_company_category(category_id: int, payload: MasterUpdateRequest, db: Session) -> CompanyCategoryMaster:
        item = db.query(CompanyCategoryMaster).filter(CompanyCategoryMaster.id == category_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Category not found.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        return item

    # ─── Seed all masters ─────────────────────────────────────────────────────

    @staticmethod
    def seed_masters(db: Session) -> None:
        if not db.query(GenderMaster).first():
            db.add_all([
                GenderMaster(code="MALE",   label="Male"),
                GenderMaster(code="FEMALE", label="Female"),
                GenderMaster(code="OTHER",  label="Other"),
            ])

        if not db.query(EmploymentTypeMaster).first():
            db.add_all([
                EmploymentTypeMaster(code="SALARIED",      label="Salaried"),
                EmploymentTypeMaster(code="SELF_EMPLOYED", label="Self Employed"),
            ])

        if not db.query(CompanyTypeMaster).first():
            db.add_all([
                CompanyTypeMaster(code="PRIVATE_LTD",   label="Private Limited"),
                CompanyTypeMaster(code="PUBLIC_LTD",    label="Public Limited"),
                CompanyTypeMaster(code="PARTNERSHIP",   label="Partnership"),
                CompanyTypeMaster(code="PROPRIETORSHIP",label="Proprietorship"),
                CompanyTypeMaster(code="LLP",           label="Limited Liability Partnership"),
                CompanyTypeMaster(code="GOVT",          label="Government"),
            ])

        if not db.query(CompanyIndustryMaster).first():
            db.add_all([
                CompanyIndustryMaster(code="IT",            label="Information Technology"),
                CompanyIndustryMaster(code="FINANCE",       label="Finance & Banking"),
                CompanyIndustryMaster(code="MANUFACTURING", label="Manufacturing"),
                CompanyIndustryMaster(code="HEALTHCARE",    label="Healthcare"),
                CompanyIndustryMaster(code="RETAIL",        label="Retail"),
                CompanyIndustryMaster(code="EDUCATION",     label="Education"),
                CompanyIndustryMaster(code="CONSTRUCTION",  label="Construction"),
                CompanyIndustryMaster(code="OTHERS",        label="Others"),
            ])

        if not db.query(CompanyCategoryMaster).first():
            db.add_all([
                CompanyCategoryMaster(code="CAT_A", label="CAT - A"),
                CompanyCategoryMaster(code="CAT_B", label="CAT - B"),
                CompanyCategoryMaster(code="CAT_C", label="CAT - C"),
                CompanyCategoryMaster(code="CAT_D", label="CAT - D"),
            ])

        db.commit()
