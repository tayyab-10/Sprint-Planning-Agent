import asyncio
from db.mongo import db

async def seed():
    print("🌱 Seeding database: nexa_db ...")

    # Clear old data
    await db["Tasks"].delete_many({})
    await db["Sprints"].delete_many({})
    await db["Users"].delete_many({})
    await db["Notifications"].delete_many({})

    # Seed Users
    users = [
        {"name": "Alice", "role": "Developer"},
        {"name": "Bob", "role": "Scrum Master"},
        {"name": "Charlie", "role": "Product Owner"},
    ]
    await db["Users"].insert_many(users)
    print("✅ Inserted Users")

    # Seed Tasks
    tasks = [
        {"title": "Setup project repo", "status": "done"},
        {"title": "Design database schema", "status": "in-progress"},
        {"title": "Implement login API", "status": "todo"},
    ]
    await db["Tasks"].insert_many(tasks)
    print("✅ Inserted Tasks")

    # Seed Sprints
    sprints = [
        {"name": "Sprint 1", "goal": "Setup project structure"},
        {"name": "Sprint 2", "goal": "Implement core features"},
    ]
    await db["Sprints"].insert_many(sprints)
    print("✅ Inserted Sprints")

    # Seed Notifications
    notifications = [
        {"message": "Sprint 1 created", "type": "system"},
        {"message": "Task assigned to Alice", "type": "task"},
    ]
    await db["Notifications"].insert_many(notifications)
    print("✅ Inserted Notifications")

    print("🎉 Database seeding completed!")

if __name__ == "__main__":
    asyncio.run(seed())
