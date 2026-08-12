from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
from src.db.models import Asset, User
from app.auth_utils import get_current_user, get_db

router = APIRouter(
    prefix="/assets",
    tags=["assets"]
)

class AssetCreate(BaseModel):
    name: str
    power_capacity_mw: float
    energy_capacity_mwh: float

class AssetResponse(AssetCreate):
    id: int
    org_id: int

    class Config:
        from_attributes = True

@router.get("", response_model=List[AssetResponse])
async def get_assets(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Asset).where(Asset.org_id == current_user.org_id))
    assets = result.scalars().all()
    return assets

@router.post("", response_model=AssetResponse)
async def create_asset(asset_data: AssetCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_asset = Asset(
        org_id=current_user.org_id,
        name=asset_data.name,
        power_capacity_mw=asset_data.power_capacity_mw,
        energy_capacity_mwh=asset_data.energy_capacity_mwh
    )
    db.add(new_asset)
    await db.commit()
    await db.refresh(new_asset)
    return new_asset

@router.delete("/{asset_id}")
async def delete_asset(asset_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Asset).where(Asset.id == asset_id, Asset.org_id == current_user.org_id))
    asset = result.scalars().first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    await db.delete(asset)
    await db.commit()
    return {"detail": "Asset deleted successfully"}
