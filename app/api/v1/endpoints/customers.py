from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.middleware.auth import get_current_super_admin
from app.models.user import UserStatus
from app.schemas.user import (
    CustomerResponse, CustomerListResponse,
    AdminUpdateCustomerRequest, APIResponse
)
from app.services.customer_service import CustomerService

router = APIRouter(
    prefix="/admin/customers",
    tags=["Super Admin — Customer Management"],
    dependencies=[Depends(get_current_super_admin)],
)


@router.get("/", response_model=CustomerListResponse, summary="List all customers (paginated)")
def list_customers(
    page:     int                  = Query(default=1,    ge=1),
    per_page: int                  = Query(default=20,   ge=1, le=100),
    search:   Optional[str]        = Query(default=None, description="Search by name, email, or mobile"),
    status:   Optional[UserStatus] = Query(default=None, description="Filter by account status"),
    db:       Session              = Depends(get_db),
):
    return CustomerService.list_customers(db, page, per_page, search, status)


@router.get("/{customer_id}", response_model=CustomerResponse, summary="Get customer by ID")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return CustomerService.get_customer(customer_id, db)


@router.patch("/{customer_id}", response_model=CustomerResponse, summary="Update customer basic details")
def update_customer(
    customer_id: int,
    payload: AdminUpdateCustomerRequest,
    db: Session = Depends(get_db),
):
    return CustomerService.admin_update_customer(customer_id, payload, db)


@router.delete("/{customer_id}", response_model=APIResponse, summary="Soft-delete a customer")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    CustomerService.delete_customer(customer_id, db)
    return APIResponse(success=True, message="Customer account has been deactivated successfully.")
