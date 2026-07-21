from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from backend.models.schemas import UserProfileSchema
from backend.models.database import get_user_profile, update_user_profile

router = APIRouter()

class UserProfileUpdate(BaseModel):
    personal_details: dict = Field(..., description="User's personal details")
    financial_details: dict = Field(..., description="User's financial details")

@router.get("/user-profile/{user_id}", response_model=UserProfileSchema)
async def get_user_profile_endpoint(user_id: str):
    """
    Endpoint to fetch user profile.
    """
    try:
        profile = await get_user_profile(user_id)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user profile: {str(e)}")

@router.put("/user-profile/{user_id}", response_model=UserProfileSchema)
async def update_user_profile_endpoint(user_id: str, profile_update: UserProfileUpdate):
    """
    Endpoint to update user profile.
    """
    try:
        updated_profile = await update_user_profile(user_id, profile_update.dict())
        return updated_profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user profile: {str(e)}")