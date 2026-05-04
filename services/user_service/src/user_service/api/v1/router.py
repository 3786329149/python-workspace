from fastapi import APIRouter

from user_service.api.v1 import rbac, users

router = APIRouter()
router.include_router(users.router)
router.include_router(rbac.router)
router.include_router(rbac.roles_router)
