# verify_db.py
import asyncio
from db.mongo import db

async def verify():
    print("🔎 Verifying MongoDB collections...\n")

    users = await db["Users"].find_one()
    tasks = await db["Tasks"].find_one()
    sprints = await db["Sprints"].find_one()
    notifications = await db["Notifications"].find_one()

    print("👤 Users:", users)
    print("📝 Tasks:", tasks)
    print("🏃 Sprints:", sprints)
    print("🔔 Notifications:", notifications)

if __name__ == "__main__":
    asyncio.run(verify())
