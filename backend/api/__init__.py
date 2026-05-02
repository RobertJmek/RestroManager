from fastapi import APIRouter

from api.auth import router as auth_router
from api.orders import router as orders_router
from api.dashboards import router as dashboards_router
from api.users import router as users_router

api_router = APIRouter()

# Asamblăm toate rutele standard HTTP API
api_router.include_router(auth_router)
api_router.include_router(orders_router)
api_router.include_router(dashboards_router)
api_router.include_router(users_router)
