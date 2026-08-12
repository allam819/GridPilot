import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.db.models import Base, engine, AsyncSessionLocal, Organization

async def migrate():
    async with engine.begin() as conn:
        print("Running Auth migration...")
        await conn.run_sync(Base.metadata.create_all)
        print("Auth tables created successfully.")
        
    async with AsyncSessionLocal() as session:
        # Create a default organization if none exists
        from sqlalchemy.future import select
        result = await session.execute(select(Organization).where(Organization.name == "DefaultOrg"))
        org = result.scalars().first()
        if not org:
            org = Organization(name="DefaultOrg")
            session.add(org)
            await session.commit()
            print(f"Created default organization with ID {org.id}")

if __name__ == "__main__":
    asyncio.run(migrate())
