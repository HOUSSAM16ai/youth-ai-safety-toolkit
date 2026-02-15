import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment.")
    sys.exit(1)

# Ensure sync driver
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
else:
    SYNC_DATABASE_URL = DATABASE_URL

SCHEMAS = [
    "planning",
    "memory",
    "user_service",  # Avoid keyword 'user'
    "research",
    "reasoning",
    "observability",
]

def init_schemas():
    print(f"Connecting to database: {SYNC_DATABASE_URL.split('@')[-1]}")  # Mask password
    engine = create_engine(SYNC_DATABASE_URL)

    with engine.connect() as connection:
        for schema in SCHEMAS:
            print(f"Creating schema if not exists: {schema}")
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        connection.commit()

    print("Schema initialization complete.")

if __name__ == "__main__":
    try:
        init_schemas()
    except Exception as e:
        print(f"Error initializing schemas: {e}")
        sys.exit(1)
