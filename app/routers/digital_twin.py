from fastapi import APIRouter
from pydantic import BaseModel, Field
from celery.result import AsyncResult
from app.worker import run_digital_twin_task, celery_app
from fastapi import Depends
from app.auth_utils import get_current_user, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.db.models import User, DigitalTwinSimulation

router = APIRouter(
    prefix="/simulate",
    tags=["digital-twin"]
)

class BatteryConfig(BaseModel):
    name: str
    power_capacity_mw: float
    energy_capacity_mwh: float
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    initial_soc_mwh: float = 0.0

class DigitalTwinRequest(BaseModel):
    baseline_config: BatteryConfig
    target_config: BatteryConfig
    capex_per_mwh: float = Field(..., description="Estimated capital expenditure per MWh of new battery capacity.")

class DigitalTwinResponse(BaseModel):
    task_id: str
    status: str

@router.post("/digital-twin", response_model=DigitalTwinResponse)
def run_digital_twin(request: DigitalTwinRequest, current_user: User = Depends(get_current_user)):
    """
    Dispatches a Celery task that runs the MPC backtest for both the baseline
    and target configurations over the historical period.
    """
    task = run_digital_twin_task.delay(
        request.baseline_config.model_dump(), 
        request.target_config.model_dump(), 
        request.capex_per_mwh
    )
    return DigitalTwinResponse(task_id=task.id, status="PENDING")

@router.get("/tasks/{task_id}")
async def get_dt_task_status(task_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Queries Celery and returns the structured comparative financials.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status
    }
    
    if task_result.status == "SUCCESS":
        # Ensure distinct separation as requested
        payload = task_result.result.get('results', {})
        response["baseline_config"] = payload.get('baseline_config')
        response["target_config"] = payload.get('target_config')
        response["comparative_analysis"] = payload.get('comparative_analysis')
        
        # Persist to database if not already persisted
        existing = await db.execute(select(DigitalTwinSimulation).where(DigitalTwinSimulation.task_id == task_id))
        if not existing.scalars().first():
            new_sim = DigitalTwinSimulation(
                org_id=current_user.org_id,
                task_id=task_id,
                baseline_config=response["baseline_config"],
                target_config=response["target_config"],
                comparative_analysis=response["comparative_analysis"]
            )
            db.add(new_sim)
            await db.commit()
            
    elif task_result.status == "FAILURE":
        response["error"] = str(task_result.result)
        
    return response
