import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load env from .env file
load_dotenv()

async def test_db(name, url):
    if not url:
        print(f"[{name}] URL is empty")
        return
    print(f"[{name}] Original URL: {url.split('@')[-1]}")
    # Ensure it starts with postgresql+asyncpg
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        
    # Clean Neon's query parameters for asyncpg compatibility
    # asyncpg doesn't support 'sslmode', only 'ssl=require'
    if "sslmode=" in url:
        url = url.split("?")[0] + "?ssl=require"
    
    print(f"[{name}] Cleaned URL: {url.split('@')[-1]}")
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print(f"[{name}] SUCCESS: Got {res.scalar()}")
        await engine.dispose()
    except Exception as e:
        print(f"[{name}] FAILED: {e}")

async def main():
    neon_url = None
    supabase_url = None
    with open(".env", "r") as f:
        for line in f:
            if "neondb" in line and "DATABASE_URL" in line:
                neon_url = line.split("=", 1)[1].strip()
            elif "supabase" in line and "DATABASE_URL" in line:
                supabase_url = line.split("=", 1)[1].strip()
                
    await test_db("Neon", neon_url)
    await test_db("Supabase", supabase_url)

if __name__ == "__main__":
    asyncio.run(main())
