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

echo "Waiting for Keystone service to start..."
until curl -s -o /dev/null $KEYSTONE_URL; do
  sleep 5
  echo "Waiting for Keystone..."
done

echo "Keystone service is up. Attempting to authenticate..."

# Get an authentication token using admin credentials
RESPONSE=$(curl -s -i -X POST $KEYSTONE_URL/auth/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "auth": {
      "identity": {
        "methods": ["password"],
        "password": {
          "user": {
            "name": "'"$ADMIN_USER"'",
            "domain": { "name": "'"$ADMIN_DOMAIN"'" },
            "password": "'"$ADMIN_PASS"'"
          }
        }
      },
      "scope": {
        "project": {
          "name": "'"$ADMIN_PROJECT"'",
          "domain": { "name": "'"$ADMIN_DOMAIN"'" }
        }
      }
    }
  }')

# Extract the token from the response headers
TOKEN=$(echo "$RESPONSE" | grep -Fi X-Subject-Token | awk '{print $2}' | tr -d '\r')

if [ -z "$TOKEN" ]; then
  echo "Failed to obtain an authentication token."
  echo "Response: $RESPONSE"
  exit 1
fi

echo "Token obtained successfully. Proceeding with Barbican service registration..."

# Register Barbican service in Keystone
SERVICE_ID=$(curl -s -X POST $KEYSTONE_URL/services \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "service": {
      "name": "barbican",
      "type": "key-manager",
      "description": "Key Manager Service"
    }
  }' | jq -r .service.id)

if [ -z "$SERVICE_ID" ]; then
  echo "Failed to register Barbican service."
  exit 1
fi

# Create Barbican endpoints in Keystone
echo "Creating Barbican endpoints in Keystone..."
for endpoint in public internal admin; do
  curl -s -X POST $KEYSTONE_URL/endpoints \
    -H "X-Auth-Token: $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "endpoint": {
        "interface": "'"$endpoint"'",
        "region": "'"$REGION_ID"'",
        "service_id": "'"$SERVICE_ID"'",
        "url": "http://'"$BARBICAN_HOST:$BARBICAN_PORT"'/v1"
      }
    }'
done

echo "Barbican service registered and endpoints created successfully."
