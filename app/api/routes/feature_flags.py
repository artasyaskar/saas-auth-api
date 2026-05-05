"""Feature Flags API Routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.services.feature_flags import FeatureFlagService, RolloutStrategy, FlagContext
from app.core.security import get_current_user

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


class CreateFlagRequest(BaseModel):
    name: str
    description: str
    default_value: bool = False
    strategy: str = "all_users"
    rollout_percentage: int = 0
    target_users: Optional[List[int]] = None
    target_attributes: Optional[dict] = None


@router.post("/")
async def create_flag(request: CreateFlagRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FeatureFlagService(db)
    flag = service.create_flag(
        name=request.name,
        description=request.description,
        default_value=request.default_value,
        strategy=RolloutStrategy(request.strategy),
        rollout_percentage=request.rollout_percentage,
        target_users=request.target_users,
        target_attributes=request.target_attributes,
        created_by=current_user.id
    )
    return {"name": flag.name, "is_active": flag.is_active}


@router.get("/{flag_name}")
async def get_flag(flag_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FeatureFlagService(db)
    status = service.get_flag_status(flag_name)
    if not status:
        raise HTTPException(status_code=404, detail="Flag not found")
    return status


@router.get("/")
async def list_flags(active_only: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FeatureFlagService(db)
    return service.get_all_flags(active_only=active_only)


@router.post("/{flag_name}/evaluate")
async def evaluate_flag(flag_name: str, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FeatureFlagService(db)
    context = FlagContext(user_id=user_id or current_user.id)
    is_enabled = service.is_enabled(flag_name, context)
    return {"flag_name": flag_name, "enabled": is_enabled}


@router.put("/{flag_name}")
async def update_flag(flag_name: str, is_active: Optional[bool] = None, rollout_percentage: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FeatureFlagService(db)
    updates = {}
    if is_active is not None:
        updates["is_active"] = is_active
    if rollout_percentage is not None:
        updates["rollout_percentage"] = rollout_percentage
    flag = service.update_flag(flag_name, **updates)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"name": flag.name, "is_active": flag.is_active}


@router.delete("/{flag_name}")
async def delete_flag(flag_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FeatureFlagService(db)
    success = service.delete_flag(flag_name)
    if not success:
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"message": "Flag deleted successfully"}


@router.post("/{flag_name}/rollback")
async def rollback_flag(flag_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FeatureFlagService(db)
    success = service.rollback_flag(flag_name)
    if not success:
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"message": "Flag rolled back successfully"}


@router.get("/{flag_name}/history")
async def get_flag_history(flag_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FeatureFlagService(db)
    return service.get_flag_history(flag_name)
