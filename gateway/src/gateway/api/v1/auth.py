from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
import httpx
from gateway.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)

class RegisterResponse(BaseModel):
    user_id: str
    email: str
    username: str
    message: str

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Create User in user-service
        try:
            user_resp = await client.post(
                f"{settings.USER_SERVICE_URL}/api/v1/users",
                json={
                    "email": str(payload.email),
                    "username": payload.username
                }
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()
            user_id = user_data["id"]
        except httpx.HTTPStatusError as e:
            # Handle specific error from user-service
            detail = e.response.json().get("message", "Failed to create user profile")
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"User service error: {str(e)}"
            )

        # 2. Bind Password in auth-service
        try:
            auth_resp = await client.post(
                f"{settings.AUTH_SERVICE_URL}/api/v1/auth/bind-password",
                json={
                    "user_id": user_id,
                    "username": payload.username,
                    "password": payload.password
                }
            )
            auth_resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # CRITICAL: In a production system, we should trigger a compensation (delete user)
            # For now, we report the error.
            detail = e.response.json().get("message", "Failed to bind authentication")
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Auth service error: {str(e)}"
            )

        return RegisterResponse(
            user_id=user_id,
            email=str(payload.email),
            username=payload.username,
            message="User registered and password bound successfully"
        )
