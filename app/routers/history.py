from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.auth_utils import get_current_user, get_db
from src.db.models import User, DigitalTwinSimulation

router = APIRouter(
    prefix="/history",
    tags=["digital-twin-history"]
)

@router.get("", response_model=List[dict])
async def get_history(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Fetch all past Digital Twin simulations for the organization."""
    result = await db.execute(
        select(DigitalTwinSimulation)
        .where(DigitalTwinSimulation.org_id == current_user.org_id)
        .order_by(DigitalTwinSimulation.created_at.desc())
    )
    simulations = result.scalars().all()
    
    return [
        {
            "id": sim.id,
            "task_id": sim.task_id,
            "created_at": sim.created_at.isoformat(),
            "baseline_config": sim.baseline_config,
            "target_config": sim.target_config,
            "comparative_analysis": sim.comparative_analysis
        }
        for sim in simulations
    ]

@router.delete("/{simulation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(simulation_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete a specific Digital Twin simulation."""
    result = await db.execute(
        select(DigitalTwinSimulation)
        .where(DigitalTwinSimulation.id == simulation_id)
        .where(DigitalTwinSimulation.org_id == current_user.org_id)
    )
    sim = result.scalars().first()
    
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
        
    await db.delete(sim)
    await db.commit()
    return None
