from fastapi import FastAPI
from app.routes.sprint_routes import router as sprint_router

app = FastAPI(title="NEXA Sprint Planner Agent")

app.include_router(sprint_router, prefix="/api/sprint", tags=["Sprint Planner"])

@app.get("/")
async def root():
    return {"message": "Sprint Planner Agent is active 🚀"}
