from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.middleware.auth import get_current_customer
from app.models.user import User
from app.schemas.user import CustomerProfileUpdateRequest, CustomerProfileResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customer", tags=["Customer — Profile"])


@router.patch(
    "/profile",
    response_model=CustomerProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update my profile",
    description=(
        "Customer updates their own extended profile after registration. "
        "PAN is encrypted before storage and never returned in plain text. "
        "For salaried customers, select company_id from the companies list. "
        "For self-employed, provide business_name instead."
    ),
)
def update_my_profile(
    payload: CustomerProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer),
):
    return CustomerService.update_profile(current_user.id, payload, db)


@router.get(
    "/profile",
    response_model=CustomerProfileResponse,
    summary="Get my profile",
)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer),
):
    from app.models.user import CustomerProfile
    from sqlalchemy.orm import joinedload
    profile = (
        db.query(CustomerProfile)
        .options(
            joinedload(CustomerProfile.gender_master),
            joinedload(CustomerProfile.employment_type_master),
            joinedload(CustomerProfile.company),
        )
        .filter(CustomerProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please update your profile first.",
        )
    from app.services.customer_service import _build_profile_response
    return _build_profile_response(profile)
