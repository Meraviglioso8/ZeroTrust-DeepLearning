#!/bin/bash

# Run the server script in the background
/usr/local/bin/bootstrap.sh &

# Wait for the server to be ready by checking the port
while ! nc -z localhost 5000; do   
echo "Waiting for Keystone API to be available..."
  sleep 2
done

# Run the second script
/usr/local/bin/initial.sh
