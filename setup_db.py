import asyncio
from ATs_breaker.infrastructure.db.database import create_db_and_tables

if __name__ == "__main__":
    asyncio.run(create_db_and_tables())
    print("Tables created.")