from fastapi import APIRouter
from app.api.v1.endpoints import auth, customers, profile, masters, companies

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(profile.router)
api_router.include_router(masters.router)
api_router.include_router(companies.router)
