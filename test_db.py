# test_db.py
import asyncio
import asyncpg

async def test_connection():
    try:
        conn = await asyncpg.connect(
            user='msa_xfxg_user',
            password='plk1hRKMcsWi7LiLLq0wLbccgR3Ki71u',
            database='msa_xfxg',
            host='dpg-d4ha3d95pdvs7393ojpg-a.oregon-postgres.render.com',
            port=5432,
            timeout=10
        )
        print("✅ Successfully connected to Render PostgreSQL!")
        await conn.close()
    except Exception as e:
        print("❌ Connection failed:", e)

asyncio.run(test_connection())