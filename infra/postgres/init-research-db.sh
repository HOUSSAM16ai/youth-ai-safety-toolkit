#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "research_db" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS research;
EOSQL
