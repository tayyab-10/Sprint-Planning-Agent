import asyncio
from db.mongo import db

async def test():
    try:
        # just fetch one document to test
        result = await db["Tasks"].find_one({})
        print("✅ Connected to MongoDB. Example document:", result)
    except Exception as e:
        print("❌ Error connecting:", e)

asyncio.run(test())
