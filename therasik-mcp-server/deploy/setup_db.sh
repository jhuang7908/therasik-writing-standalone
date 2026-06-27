#!/bin/bash
set -e

DB_NAME="therasik_mcp"
DB_USER="therasik"
DB_PASS="therasik_mcp_2026"

echo "[db] Creating role $DB_USER if not exists..."
sudo -u postgres psql -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='$DB_USER') THEN CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS'; END IF; END \$\$;"

echo "[db] Creating database $DB_NAME if not exists..."
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "[db] Applying schema..."
sudo -u postgres psql -d $DB_NAME -f /opt/therasik-mcp/server/schema/init.sql

echo "[db] SCHEMA_OK"
