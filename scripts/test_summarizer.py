import asyncio
import json
from app.models.task import Task
from app.core.summarizer import generate_sprint_summary

async def main():
    tasks = [
        Task(**{"_id":"t1","title":"Implement login","priority":"High","status":"Open","assignedTo":"m1","dueDate":None,"estimatedHours":8.0}),
        Task(**{"_id":"t2","title":"Write unit tests","priority":"Medium","status":"Open","assignedTo":"m2","dueDate":None,"estimatedHours":6.0}),
    ]
    summary = await generate_sprint_summary(tasks)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
