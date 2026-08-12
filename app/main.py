from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, backtest, digital_twin, assets, history

app = FastAPI(
    title="GridPilot API",
    description="Backend for GridPilot AI-driven VPP",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1/simulate")
app.include_router(backtest.router, prefix="/api/v1")
app.include_router(digital_twin.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the GridPilot API"}
