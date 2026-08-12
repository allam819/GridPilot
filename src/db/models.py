import asyncio
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import os

# Neon gives us postgresql:// but we need postgresql+asyncpg:// for async SQLAlchemy
raw_db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://gridpilot:gridpilot_secret@localhost:5432/gridpilot")
if raw_db_url.startswith("postgresql://"):
    DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = raw_db_url

# asyncpg does not support the sslmode parameter, so we strip it if present
DATABASE_URL = DATABASE_URL.replace("?sslmode=require", "").replace("&sslmode=require", "")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    power_capacity_mw = Column(Float, nullable=False)
    energy_capacity_mwh = Column(Float, nullable=False)

class MarketData(Base):
    __tablename__ = "market_data"
    
    timestamp = Column(DateTime, primary_key=True, index=True)
    solar_generation_mw = Column(Float, nullable=False)
    price_usd_per_mwh = Column(Float, nullable=False)
    ancillary_price_usd_per_mw = Column(Float, nullable=False)

class OptimizerSchedule(Base):
    __tablename__ = "optimizer_schedule"
    
    timestamp = Column(DateTime, primary_key=True, index=True)
    optimal_charge_mw = Column(Float, nullable=False)
    optimal_discharge_mw = Column(Float, nullable=False)
    optimal_reserve_mw = Column(Float, nullable=False)
    optimal_soc_mwh = Column(Float, nullable=False)
    explanation = Column(String, nullable=True)

class DigitalTwinSimulation(Base):
    __tablename__ = "digital_twin_simulations"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    task_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    baseline_config = Column(JSONB, nullable=False)
    target_config = Column(JSONB, nullable=False)
    comparative_analysis = Column(JSONB, nullable=False)

async def init_db():
    async with engine.begin() as conn:
        # Create standard tables
        await conn.run_sync(Base.metadata.create_all)
        
        # Convert to TimescaleDB hypertables
        # MarketData Hypertable
        await conn.execute(text(
            "SELECT create_hypertable('market_data', 'timestamp', if_not_exists => TRUE);"
        ))
        # OptimizerSchedule Hypertable
        await conn.execute(text(
            "SELECT create_hypertable('optimizer_schedule', 'timestamp', if_not_exists => TRUE);"
        ))
        
    print("Database schema and hypertables initialized.")

if __name__ == "__main__":
    asyncio.run(init_db())
