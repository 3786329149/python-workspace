from fastapi import APIRouter

from user_service.api.v1 import users

router = APIRouter()
router.include_router(users.router)
