# 0. Fill out your SOURCE and DESTINATION DB Credentials.
cp .env.sample .env
source .env

# 1. Perform Migrations
docker run --add-host=host.docker.internal:host-gateway --rm ghcr.io/cowprotocol/solver-rewards-db-migration -url=jdbc:postgresql://$DEST_HOST/$DEST_DB -user=$DEST_ADMIN_USER -password=$DEST_ADMIN_PASSWORD migrate

# 2. Tenderly Redirect (update secret)
# Update DATABASE_URL at https://dashboard.tenderly.co/gp-v2/solver-slippage/actions/secrets with
export DEST_WRITE_URL=postgresql://${DEST_WRITE_USER}:${DEST_WRITE_PASSWORD}@${DEST_HOST}:${DEST_PORT}/${DEST_DB}
echo $DEST_WRITE_URL

# 3. Create Backup of SOURCE DB (excluding flyaway_migrations)
pg_dump --host $SOURCE_HOST --port $SOURCE_PORT --user $SOURCE_USER --data-only --exclude-table public.flyway_schema_history > backup.sql

# 4. Import this backup
psql -h $DEST_HOST -U $DEST_WRITE_USER -d $DEST_DB -a -f ./backup.sql

# 5. Update `WAREHOUSE_URL` in dune-sync configuration in https://github.com/cowprotocol/infrastructure/
export DEST_READ_URL=${DEST_READ_USER}:${DEST_READ_PASSWORD}@${DEST_HOST}:${DEST_PORT}/${DEST_DB}
pulumi config set --secret warehouseUrl $DEST_READ_URL
