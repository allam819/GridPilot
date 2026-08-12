from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from celery.result import AsyncResult
from app.worker import run_mpc_backtest_task, celery_app
from fastapi import Depends
from app.auth_utils import get_current_user, get_db
from src.db.models import User, Asset
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/backtest",
    tags=["backtest"]
)

class BacktestRequest(BaseModel):
    start_date: str = Field(..., description="Start date of the backtest (YYYY-MM-DD)", example="2025-07-01")
    end_date: str = Field(..., description="End date of the backtest (YYYY-MM-DD)", example="2025-07-31")
    asset_ids: list[int] = Field(None, description="Optional list of asset IDs to include. If empty, includes all organization assets.")

class BacktestResponse(BaseModel):
    task_id: str
    status: str

@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Dispatches the heavy MPC backtest simulation as an asynchronous Celery task.
    Immediately returns a task_id.
    """
    # Fetch user's actual assets
    query = select(Asset).where(Asset.org_id == current_user.org_id)
    if request.asset_ids:
        query = query.where(Asset.id.in_(request.asset_ids))
        
    result = await db.execute(query)
    assets = result.scalars().all()
    
    if not assets:
        raise HTTPException(status_code=400, detail="No assets found to simulate.")
    
    nodes_payload = [
        {
            "name": asset.name,
            "power_capacity_mw": asset.power_capacity_mw,
            "energy_capacity_mwh": asset.energy_capacity_mwh
        } for asset in assets
    ]
    
    # Send dynamic nodes to Celery
    task = run_mpc_backtest_task.delay(request.start_date, request.end_date, nodes_payload)
    return BacktestResponse(task_id=task.id, status="PENDING")

@router.get("/tasks/{task_id}")
def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    """
    Queries Celery and returns the current status (PENDING, SUCCESS, FAILURE).
    If successful, returns the final financial metrics.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status
    }
    
    if task_result.status == "SUCCESS":
        response["result"] = task_result.result
    elif task_result.status == "FAILURE":
        response["error"] = str(task_result.result)
        
    return response
