import pandas as pd
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from .models import MarketData, OptimizerSchedule, AsyncSessionLocal

class TimescaleRepository:
    def __init__(self, session_maker=AsyncSessionLocal):
        self.session_maker = session_maker
        
    async def bulk_insert_market_data(self, df: pd.DataFrame):
        """
        Rapidly bulk inserts synthetic market data into the TimescaleDB hypertable.
        """
        records = df.to_dict(orient='records')
        # Map DataFrame columns to model if necessary
        # Ensure timestamp is a python datetime object
        
        db_records = [
            MarketData(
                timestamp=row['timestamp'],
                solar_generation_mw=row['solar_generation_mw'],
                price_usd_per_mwh=row['price_usd_per_mwh'],
                ancillary_price_usd_per_mw=row.get('ancillary_price_usd_per_mw', 0.0)
            )
            for row in records
        ]
        
        print(f"Bulk inserting {len(db_records)} records into MarketData...")
        async with self.session_maker() as session:
            session.add_all(db_records)
            await session.commit()
        print("Bulk insert complete.")

    async def get_market_data_window(self, start_time, end_time) -> pd.DataFrame:
        """
        Fetch a specific window of market data from the DB for the MPC lookahead.
        (Implemented for completeness, though our current MPC runner slices a DataFrame directly).
        """
        from sqlalchemy import select
        async with self.session_maker() as session:
            stmt = select(MarketData).where(
                MarketData.timestamp >= start_time,
                MarketData.timestamp < end_time
            ).order_by(MarketData.timestamp.asc())
            
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            # Convert back to DataFrame
            df = pd.DataFrame([{
                'timestamp': r.timestamp,
                'solar_generation_mw': r.solar_generation_mw,
                'price_usd_per_mwh': r.price_usd_per_mwh,
                'ancillary_price_usd_per_mw': r.ancillary_price_usd_per_mw
            } for r in records])
            
            return df
            
    async def insert_schedule(self, record: dict):
        """
        Insert a single executed schedule step.
        """
        db_record = OptimizerSchedule(
            timestamp=record['timestamp'],
            optimal_charge_mw=record['charge_mw'],
            optimal_discharge_mw=record['discharge_mw'],
            optimal_reserve_mw=record.get('reserve_mw', 0.0),
            optimal_soc_mwh=record['actual_soc_mwh']
        )
        async with self.session_maker() as session:
            session.add(db_record)
            await session.commit()
