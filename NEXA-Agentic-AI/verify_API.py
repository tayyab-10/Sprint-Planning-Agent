# verify_api.py
from fastapi import FastAPI
from db.mongo import db
import uvicorn

app = FastAPI(title="NEXA DB Verification API")

@app.get("/verify")
async def verify_db():
    collections = ["Users", "Tasks", "Sprints", "Notifications"]
    results = {}

    for col in collections:
        count = await db[col].count_documents({})
        latest = await db[col].find().sort("_id", -1).limit(1).to_list(length=1)

        results[col] = {
            "count": count,
            "latest": latest[0] if latest else None
        }

    return {
        "status": "success",
        "database": db.name,
        "collections": results
    }

if __name__ == "__main__":
    uvicorn.run("verify_api:app", host="0.0.0.0", port=8000, reload=True)
