import asyncio
from db.database import create_db_and_tables

if __name__ == "__main__":
    asyncio.run(create_db_and_tables())
    print("Tables created.")