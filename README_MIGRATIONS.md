# Database Migration Strategy

This repository has transitioned from a monolithic migration strategy to a microservices-based migration strategy.
Each microservice now manages its own database schema independently, ensuring better isolation and scalability.

## Overview

The database is divided into logical schemas, one for each service:
- `planning_agent` -> schema: `planning`
- `memory_agent` -> schema: `memory`
- `user_service` -> schema: `user_service`
- `observability_service` -> schema: `observability`

## How to Run Migrations

You can run migrations for each service independently using `alembic`.

### Prerequisites

Ensure you have the necessary dependencies installed:
```bash
pip install -r requirements.txt
```

### Running Migrations for a Service

Navigate to the service directory and run `alembic` commands.

Example for `planning_agent`:

1.  **Navigate to the service directory:**
    ```bash
    cd microservices/planning_agent
    ```

2.  **Generate a new migration (autogenerate):**
    Ensure your database is running and accessible via `DATABASE_URL`.
    ```bash
    # Replace with your actual database URL if not set in .env
    export DATABASE_URL="postgresql+asyncpg://user:password@host:port/dbname"
    alembic revision --autogenerate -m "description_of_changes"
    ```

3.  **Apply migrations:**
    ```bash
    alembic upgrade head
    ```

### Running Migrations for All Services

A helper script is provided to apply migrations for all services (future implementation in `toolkit/migrations`).
Currently, you must run them individually.

## Troubleshooting

-   **"relation does not exist"**: Ensure you are running the migration for the correct service and that the schema exists. The `env.py` script attempts to set the `search_path`, but you might need to create the schema manually if it doesn't exist:
    ```sql
    CREATE SCHEMA IF NOT EXISTS planning;
    CREATE SCHEMA IF NOT EXISTS memory;
    CREATE SCHEMA IF NOT EXISTS user_service;
    CREATE SCHEMA IF NOT EXISTS observability;
    ```
-   **"alembic: command not found"**: Run `pip install alembic`.

## Legacy Migrations

The old monolithic migrations have been archived to `migrations_archive/`. Do not use them for new development.
