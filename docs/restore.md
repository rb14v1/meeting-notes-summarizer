# Database backup and restore procedure

## Backup configuration (from `infra/main.tf`)

| Setting | Value |
|---|---|
| Server | `psql-meeting-notes-summarizer` (Azure Database for PostgreSQL Flexible Server, v16) |
| Resource group | `meeting-notes-summarizer` |
| Primary region | `uksouth` |
| Automated backups | Enabled (managed by Azure, daily snapshots plus continuous WAL archiving) |
| Retention | 35 days (`backup_retention_days = 35`) |
| Geo-redundant backup | Enabled (`geo_redundant_backup_enabled = true`). Backups are copied to the paired region, `ukwest` |
| Point-in-time recovery | Supported for any point inside the 35-day retention window |

Azure always restores to a **new** server. It never overwrites the existing one.
After a restore, point the application at the new server, or swap names as
described below.

## Prerequisites

- Azure CLI (`az`) is logged in with Contributor rights on the
  `meeting-notes-summarizer` resource group.
- The restore target time in UTC (ISO 8601, for example `2026-11-17T09:30:00Z`).
  It must fall inside the retention window.
- The VNet/subnet and private DNS zone details used by `infra/main.tf`
  (`var.vnet_id`, `var.subnet_id`, `var.hub_resource_group`), so you can set up
  private access to the restored server.

## 1. Point-in-time restore (same region)

Use this for data corruption, a bad migration or accidental deletes.

```bash
az postgres flexible-server restore \
  --resource-group meeting-notes-summarizer \
  --name psql-meeting-notes-summarizer-restore-<yyyymmddhhmm> \
  --source-server psql-meeting-notes-summarizer \
  --restore-time "<UTC timestamp>"
```

To restore to the most recent available point, leave out `--restore-time`.

## 2. Geo-restore (regional outage in `uksouth`)

```bash
az postgres flexible-server geo-restore \
  --resource-group meeting-notes-summarizer \
  --name psql-meeting-notes-summarizer-geo-<yyyymmddhhmm> \
  --source-server psql-meeting-notes-summarizer \
  --location ukwest
```

Geo-restore uses the latest geo-replicated backup. Expect some data loss, up to
roughly one hour (RPO).

## 3. Network access to the restored server

The primary server has `public_network_access_enabled = false` and is reached
through the private endpoint `pe-psql-meeting-notes-summarizer`. To give the
restored server the same access:

1. Create a private endpoint for the restored server in the application
   subnet (`var.subnet_id`), with subresource `postgresqlServer`.
2. Attach it to the `privatelink.postgres.database.azure.com` private DNS zone
   in the hub resource group (`var.hub_resource_group`).

## 4. Verify the restored data

From a host that can reach the private endpoint:

```bash
psql "host=<restored-server>.postgres.database.azure.com port=5432 dbname=<db> user=psqladmin sslmode=require" \
  -c "SELECT count(*) FROM meetings_meeting;" \
  -c "SELECT max(created_at) FROM meetings_meeting;"
```

Check that the row counts and latest timestamps match what you expect for the
restore point. Then run `python manage.py migrate --check` against the restored
database from the backend.

## 5. Cut over

1. Update the backend database host setting or secret to the restored server's
   FQDN, then restart the backend.
2. Smoke-test logging in, listing meetings and summarizing a meeting.
3. Once the restored server is confirmed as the new primary, bring Terraform
   state back in line with it: either import it, or rename and re-point
   `azurerm_postgresql_flexible_server.postgresql`. Do this before the next
   `terraform apply`, so that apply does not recreate the old server.
4. Keep the old server until the incident review is finished, then delete it.

## Restore test log

Run a restore test before go-live and then at least once a year. For each test,
restore to a throwaway server, verify it (step 4), record it in the table below
and delete the test server.

| Date (UTC) | Type (PITR / geo) | Restore point | Restored server | Duration | Verified by | Result / notes |
|---|---|---|---|---|---|---|
| _pending: must be completed before go-live_ | PITR | | | | | |
