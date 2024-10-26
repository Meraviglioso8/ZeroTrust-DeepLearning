#!/bin/bash

# Environment variables for the Authentication Service database
AUTH_DB_HOST="postgres_auth"
AUTH_DB_PORT=5433
AUTH_DB_NAME="auth_db"
AUTH_DB_USER="auth_user"
AUTH_DB_PASS="auth_pass"

# Wait for PostgreSQL (Authentication Service) to be ready
echo "Waiting for PostgreSQL (Authentication Service) to start..."
until pg_isready -h $AUTH_DB_HOST -p $AUTH_DB_PORT; do
  sleep 1
done

# Run the SQL script for the Authentication Service
echo "Setting up the Authentication Service database..."
PGPASSWORD=$AUTH_DB_PASS psql -h $AUTH_DB_HOST -p $AUTH_DB_PORT -U $AUTH_DB_USER -d $AUTH_DB_NAME -f auth_service.sql

if [ $? -eq 0 ]; then
  echo "Authentication Service database setup completed!"
else
  echo "Failed to set up the Authentication Service database."
  exit 1
fi
