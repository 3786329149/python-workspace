from fastapi import APIRouter

from user_service.api.v1 import depts, rbac, users, tenants

router = APIRouter()
router.include_router(users.router)
router.include_router(rbac.router)
router.include_router(rbac.roles_router)
router.include_router(rbac.menus_router)
router.include_router(depts.router)
router.include_router(tenants.router)
