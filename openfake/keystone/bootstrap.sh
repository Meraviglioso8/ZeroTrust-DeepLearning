#!/bin/bash
# Environment variables for PostgreSQL (for Keystone)
POSTGRES_HOST=${POSTGRES_HOST:-"postgres_keystone"}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-"keystone_db"}
POSTGRES_USER=${POSTGRES_USER:-"keystone"}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-"keystonepass"}

# Environment variables for Barbican
BARBICAN_HOST=${BARBICAN_HOST:-"barbican"}
BARBICAN_PORT=${BARBICAN_PORT:-9311}

# Keystone admin credentials for service registration
ADMIN_USER=${ADMIN_USER:-"admin"}
ADMIN_PASS=${ADMIN_PASS:-"adminpass"}
ADMIN_PROJECT=${ADMIN_PROJECT:-"admin"}
ADMIN_DOMAIN=${ADMIN_DOMAIN:-"Default"}
KEYSTONE_URL=${KEYSTONE_URL:-"http://localhost:5000/v3"}
REGION_ID=$(uuidgen)

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to start..."
until pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT; do
  sleep 1
done

# Export PostgreSQL credentials for Keystone
export DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"

# Initialize Keystone database and synchronize it
echo "Running Keystone database migrations..."
keystone-manage db_sync

# Ensure the Fernet keys are created
if [ ! -d /etc/keystone/fernet-keys ]; then
  echo "Creating Fernet keys directory..."
  mkdir -p /etc/keystone/fernet-keys
  chown keystone:keystone /etc/keystone/fernet-keys
  chmod 700 /etc/keystone/fernet-keys

  # Initialize Fernet keys
  echo "Initializing Fernet keys..."
  keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone
fi

# Initialize credential keys
if [ ! -d /etc/keystone/credential-keys ]; then
  echo "Initializing credentials keys..."
  mkdir -p /etc/keystone/credential-keys
  chown keystone:keystone /etc/keystone/credential-keys
  chmod 700 /etc/keystone/credential-keys

  keystone-manage credential_setup --keystone-user keystone --keystone-group keystone
fi

# Bootstrap Keystone
echo "Bootstrapping Keystone..."
keystone-manage bootstrap \
  --bootstrap-password $ADMIN_PASS \
  --bootstrap-admin-url http://localhost:35357/v3/ \
  --bootstrap-internal-url http://localhost:5000/v3/ \
  --bootstrap-public-url http://localhost:5000/v3/ \
  --bootstrap-region-id $REGION_ID

echo "Starting Keystone service..."
uwsgi --ini /etc/keystone/keystone-uwsgi-public.ini &
uwsgi --ini /etc/keystone/keystone-uwsgi-admin.ini

