#!/bin/bash
set -e

# Create databases
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    CREATE DATABASE planning_db;
    CREATE DATABASE memory_db;
    CREATE DATABASE user_db;
    CREATE DATABASE research_db;
    CREATE DATABASE reasoning_db;
    CREATE DATABASE observability_db;
EOSQL

# Create schemas in each database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "planning_db" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS planning;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "memory_db" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS memory;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "user_db" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS user_service;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "research_db" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS research;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "reasoning_db" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS reasoning;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "observability_db" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS observability;
EOSQL
