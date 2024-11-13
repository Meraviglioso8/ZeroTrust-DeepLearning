#!/bin/bash

# Load environment variables from .env file
export $(grep -v '^#' .env | xargs)

# PostgreSQL connection details from environment variables
DB_USER="autho_user"
DB_PASSWORD="autho_pass"
DB_NAME="autho_db"
DB_HOST="localhost"
DB_PORT=5432 # Default port is 5432 if not specified
SSL_MODE=${SSL_MODE:-require}  # Default SSL mode is 'require'


# SQL command to create the permissions table
SQL_COMMAND="
CREATE TABLE IF NOT EXISTS permissions (
    user_id VARCHAR(50) PRIMARY KEY,
    permissions TEXT
);
"

# Run the SQL command
PGPASSWORD=$DB_PASSWORD psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -p "$DB_PORT" -c "$SQL_COMMAND" --set=sslmode=$SSL_MODE

# Check if the table creation was successful
if [ $? -eq 0 ]; then
    echo "Table 'permissions' created successfully."
else
    echo "Failed to create table 'permissions'."
fi
