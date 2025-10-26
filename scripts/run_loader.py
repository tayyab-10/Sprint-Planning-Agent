import asyncio
import json
import sys
from pathlib import Path
# Ensure project root is on sys.path so 'app' package can be imported when running this script directly
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.core.data_loader import DataLoader


async def main():
    loader = DataLoader("test_project")
    members = await loader.fetch_project_members()
    tasks = await loader.fetch_project_tasks()
    print("MEMBERS:")
    print(json.dumps([m.dict() for m in members], indent=2, default=str))
    print("TASKS:")
    print(json.dumps([t.dict() for t in tasks], indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
