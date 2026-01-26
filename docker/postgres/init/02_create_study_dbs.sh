#!/bin/bash
# ============================================
# Create Study Databases
# ============================================
# This script creates study databases on first PostgreSQL start

set -e

# Function to create database if not exists
create_db_if_not_exists() {
    local db_name=$1
    if ! psql -U "$POSTGRES_USER" -lqt | cut -d \| -f 1 | grep -qw "$db_name"; then
        echo "Creating database: $db_name"
        createdb -U "$POSTGRES_USER" -E UTF8 -T template0 "$db_name"
        
        # Create schemas in the study database
        psql -U "$POSTGRES_USER" -d "$db_name" -c "CREATE SCHEMA IF NOT EXISTS data;"
        psql -U "$POSTGRES_USER" -d "$db_name" -c "CREATE SCHEMA IF NOT EXISTS log;"
        psql -U "$POSTGRES_USER" -d "$db_name" -c "GRANT ALL PRIVILEGES ON SCHEMA data TO $POSTGRES_USER;"
        psql -U "$POSTGRES_USER" -d "$db_name" -c "GRANT ALL PRIVILEGES ON SCHEMA log TO $POSTGRES_USER;"
        
        echo "Database $db_name created successfully with schemas: data, log"
    else
        echo "Database $db_name already exists"
    fi
}

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -U "$POSTGRES_USER"; do
    sleep 1
done

echo "Creating study databases..."

# Create study databases
create_db_if_not_exists "db_study_43en"
create_db_if_not_exists "db_study_44en"

echo "All study databases created successfully!"
