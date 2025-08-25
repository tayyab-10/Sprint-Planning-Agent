from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
load_dotenv()  # 🔑 this loads .env

MONGO_URI = os.getenv("MONGO_URI")  # 👈 matches .env exactly
print("MONGO_URI:", MONGO_URI)


if not MONGO_URI:
    raise ValueError("❌ MONGO_URI not found in .env")

client = AsyncIOMotorClient(MONGO_URI)
db = client.get_database("NEXA")  # 👈 explicitly use NEXA database

# Collections
tasks_col = db["Tasks"]
sprints_col = db["Sprints"]
assignments_col = db["TaskAssignments"]
notifications_col = db["Notifications"]
users_col = db["Users"]
