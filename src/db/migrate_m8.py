import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://gridpilot:gridpilot_secret@localhost:5432/gridpilot"

async def run_migration():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        print("Running migration for Milestone 8...")
        try:
            await conn.execute(text(
                "ALTER TABLE optimizer_schedule ADD COLUMN IF NOT EXISTS explanation TEXT NULL;"
            ))
            print("Successfully added 'explanation' column to 'optimizer_schedule'.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_migration())
