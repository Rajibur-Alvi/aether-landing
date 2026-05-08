from fastapi import APIRouter, Depends, HTTPException
from models.schemas import (
    UserProfileResponse,
    UpdateProfileRequest,
    CommandCenterResponse,
    UpdateCommandCenterRequest,
    DarkDataResponse,
)
from middleware.auth import get_current_user
from services.supabase_service import get_supabase

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(user_id: str = Depends(get_current_user)):
    """Get current user's profile."""
    try:
        sb = get_supabase()
        result = sb.table("user_profiles") \
            .select("*") \
            .eq("id", user_id) \
            .execute()
        if result.data:
            return result.data[0]
        sb.table("user_profiles").insert({"id": user_id}).execute()
        result = sb.table("user_profiles") \
            .select("*") \
            .eq("id", user_id) \
            .execute()
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    user_id: str = Depends(get_current_user),
):
    """Update current user's profile."""
    update_data = request.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        sb = get_supabase()
        result = sb.table("user_profiles") \
            .update(update_data) \
            .eq("id", user_id) \
            .execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/command-center", response_model=CommandCenterResponse)
async def get_command_center(user_id: str = Depends(get_current_user)):
    """Get user's command center settings."""
    try:
        sb = get_supabase()
        result = sb.table("command_center_settings") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()
        if result.data:
            return result.data[0]
        sb.table("command_center_settings").insert({
            "user_id": user_id,
        }).execute()
        result = sb.table("command_center_settings") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/command-center", response_model=CommandCenterResponse)
async def update_command_center(
    request: UpdateCommandCenterRequest,
    user_id: str = Depends(get_current_user),
):
    """Update user's command center settings."""
    update_data = request.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        sb = get_supabase()
        result = sb.table("command_center_settings") \
            .update(update_data) \
            .eq("user_id", user_id) \
            .execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Settings not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dark-data", response_model=DarkDataResponse)
async def get_dark_data(
    limit: int = 50,
    user_id: str = Depends(get_current_user),
):
    """Get user's dark data event log."""
    try:
        sb = get_supabase()
        result = sb.table("dark_data_events") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return DarkDataResponse(events=result.data, total=len(result.data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
