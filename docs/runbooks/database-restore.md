# Runbook: Database Restore (Azure PostgreSQL Flexible Server)

This runbook covers how to restore the meeting-notes-summarizer database. It also holds
the record of restore tests, including the one that must be done before go-live.

## 1. Backup configuration (source of truth: `infra/main.tf`)

| Setting | Value | Where |
|---|---|---|
| Server resource | `azurerm_postgresql_flexible_server.postgresql` | `infra/main.tf` |
| Server name | `psql-test-env` | `infra/main.tf` |
| Resource group | `test-env-` | `infra/main.tf` |
| Primary region | `uksouth` | `infra/main.tf` |
| Engine version | PostgreSQL 16 | `infra/main.tf` |
| Automated backups | Enabled (Azure-managed, daily full snapshots + continuous WAL) | platform default |
| Retention | `backup_retention_days = 35` (requirement: at least 30) | `infra/main.tf` |
| Geo-redundant backup | `geo_redundant_backup_enabled = true` (copied to the paired region, `ukwest`) | `infra/main.tf` |
| Point-in-time recovery | Supported anywhere inside the 35-day retention window | platform |
| Network | Private endpoint only (`public_network_access_enabled = false`) | `infra/main.tf` |

> Note: `geo_redundant_backup_enabled` can only be set when the server is created. Changing it
> later forces Terraform to replace the server. Do not turn it off.

The application reaches the database through these environment variables (see
`backend/.env.example`): `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`.

## 2. Prerequisites

- Azure CLI 2.50 or later, logged in with `az login`, with Contributor rights on resource group `test-env-`.
- Network access to the private endpoint (run from inside the VNet, through the jump host, or from a pipeline agent with VNet access).
- `psql` client 16 or later, for checking the restore.
- The admin password (`random_password.postgresql_admin`) from Terraform state or the secret store.

```bash
RG="test-env-"
SOURCE_SERVER="psql-test-env"
```

## 3. Choosing the restore type

| Scenario | Procedure |
|---|---|
| Data was corrupted or deleted by mistake, region is healthy | Section 4: point-in-time restore (PITR) |
| Primary region (`uksouth`) is unavailable | Section 5: geo-restore to `ukwest` |
| Restore test / drill | Section 4 into a temporary server, then Section 7 |

Restores always create a **new** server. The source server is never overwritten.

## 4. Point-in-time restore (same region)

1. Find the restore point in UTC. It must fall inside the last 35 days and be no later than now.
   ```bash
   az postgres flexible-server show -g "$RG" -n "$SOURCE_SERVER" \
     --query "{earliestRestore: backup.earliestRestoreDate, retentionDays: backup.backupRetentionDays, geo: backup.geoRedundantBackup}" -o table
   ```
2. Restore to a new server:
   ```bash
   RESTORE_TIME="2026-01-01T10:00:00Z"   # replace with the target UTC timestamp
   TARGET_SERVER="psql-test-env-restore-$(date -u +%Y%m%d%H%M)"
   az postgres flexible-server restore \
     --resource-group "$RG" \
     --name "$TARGET_SERVER" \
     --source-server "$SOURCE_SERVER" \
     --restore-time "$RESTORE_TIME"
   ```
   Portal alternative: the server, then **Overview > Restore**, then **Select a custom restore point**.
3. Configure networking on the restored server. Public access stays disabled. Add a private endpoint
   that uses the same subnet and the `privatelink.postgres.database.azure.com` private DNS zone, matching
   `azurerm_private_endpoint.postgresql_pe` in `infra/main.tf`.
4. Check the data (Section 7).
5. Cut over (Section 6) or, for a partial recovery, copy the affected rows back with `pg_dump`/`psql`
   from the restored server into the primary.

## 5. Geo-restore (regional outage)

1. Confirm that `uksouth` is affected (Azure Service Health) and that the incident lead has approved failover.
2. Restore into the paired region:
   ```bash
   TARGET_SERVER="psql-test-env-geo-$(date -u +%Y%m%d%H%M)"
   az postgres flexible-server geo-restore \
     --resource-group "$RG" \
     --name "$TARGET_SERVER" \
     --source-server "$SOURCE_SERVER" \
     --location ukwest
   ```
   Expect up to about 1 hour of data loss (RPO), because geo-replicated backups lag the primary.
3. Set up private networking in `ukwest`: private endpoint plus a DNS zone link to the VNet in that region.
4. Check the data (Section 7), then cut over (Section 6).

## 6. Cut-over

1. Stop writes. Scale the backend to zero or put it in maintenance mode.
2. Point the application at the restored server by updating `POSTGRES_HOST` (and `POSTGRES_PASSWORD`
   if it changed) in the app's environment or secret store, then restart the backend.
3. Run `python manage.py migrate --check` against the restored database to confirm the schema matches.
4. Smoke test: log in, list meetings, and open one summary.
5. Update Terraform so it matches reality. Either import the restored server into state, or rename it
   in `infra/main.tf` and run `terraform plan` to make sure there is no unexpected drift. Keep the old
   server until the incident is closed, then remove it.

## 7. Checking a restore

Run these against the restored server:

```bash
psql "host=<restored-host> port=5432 dbname=<POSTGRES_DB> user=psqladmin sslmode=require" <<'SQL'
SELECT now(), version();
SELECT count(*) FROM django_migrations;
SELECT app, name FROM django_migrations ORDER BY id DESC LIMIT 5;
-- Row counts for the main application tables, compared with the source at the restore point
SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;
SQL
```

The restore passes when:
- The server is reachable through its private endpoint.
- The latest `django_migrations` entry matches the deployed release.
- Row counts for the main tables match the source as of the restore time, within the expected change.
- The application smoke test in Section 6 step 4 passes against the restored server.

Write down how long the restore took (request to server available). That is the measured RTO.

## 8. Restore test schedule

- **Before go-live:** one full PITR drill (Section 4 into a temporary server, then Section 7). Go-live is blocked until this is recorded below.
- **After that:** at least every quarter, plus after any change to backup settings in `infra/main.tf`.
- Delete temporary drill servers when the drill is done:
  `az postgres flexible-server delete -g "$RG" -n "<drill-server>" --yes`

## 9. Restore test log

Add a row for every drill. Do not fill in a row until the drill has actually been run.

| Date (UTC) | Type (PITR / geo) | Restore point | Target server | Duration (RTO) | Checks passed | Performed by | Notes |
|---|---|---|---|---|---|---|---|
| _pending: pre-go-live drill_ | PITR | | | | | | Required before go-live |
