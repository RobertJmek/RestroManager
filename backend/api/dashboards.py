from fastapi import APIRouter, Depends
from core.security import require_role

router = APIRouter(tags=["Dashboards RBAC"])

@router.get("/manager/stats", dependencies=[Depends(require_role(["Manager"]))])
async def get_manager_stats():
    return {"message": "Doar managerul vede asta", "revenue": 15000}

@router.get("/chef/active-orders", dependencies=[Depends(require_role(["Chef", "Manager"]))])
async def get_chef_orders():
    return {"message": "Bucătarul și Managerul văd asta", "orders": []}

@router.get("/waiter/tables", dependencies=[Depends(require_role(["Waiter", "Manager"]))])
async def get_waiter_tables():
    return {"message": "Chelnerul și Managerul văd asta", "tables": []}
