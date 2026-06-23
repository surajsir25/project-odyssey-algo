#!/bin/bash

# Cleanup script - stop and remove all containers

echo "Stopping Odyssey Trading System..."

docker compose down

if docker compose down -v; then
    echo "✓ Services stopped and volumes cleaned"
else
    echo "✗ Error stopping services"
    exit 1
fi

echo "Done!"
