# Database backup & restore procedure

This runbook covers the production PostgreSQL database for the Meeting Notes
& Action Items Summarizer.

## Backup configuration (from `infra/main.tf`)

| Setting | Value |
|---|---|
| Server | `psql-meeting-notes-summarizer` (Azure Database for PostgreSQL Flexible Server, v16) |
| Resource group | `meeting-notes-summarizer` |
| Primary region | `uksouth` |
| Automated backups | Enabled (managed by Azure, daily full + continuous WAL) |
| Retention | 35 days (`backup_retention_days = 35`) |
| Geo-redundant backup | Enabled (`geo_redundant_backup_enabled = true`), so backups are copied to the paired region (`ukwest`) |
| Point-in-time recovery | Supported anywhere in the 35-day retention window |

Do not lower `backup_retention_days` below 30 or turn off
`geo_redundant_backup_enabled`. Geo-redundancy can only be set when a server
is created, so changing it means recreating the server.

## When to restore

- Data was corrupted or deleted by mistake (bad migration, faulty bulk edit,
  operator error): do a **point-in-time restore** to a moment just before the
  incident.
- The primary region (`uksouth`) is unavailable: do a **geo-restore** into
  the paired region.

An Azure Flexible Server restore always creates a **new** server. It never
overwrites the existing one in place.

## Prerequisites

- Azure CLI logged in (`az login`) with Contributor rights on the
  `meeting-notes-summarizer` resource group.
- The incident time in UTC (ISO 8601, e.g. `2026-11-17T09:30:00Z`).
- Network access to the private endpoint (the server has
  `public_network_access_enabled = false`), e.g. from a jump host or the
  app's VNet.

## Procedure A: Point-in-time restore (same region)

1. Pick a restore point just before the incident, inside the last 35 days.
2. Create the restored server:

   ```bash
   az postgres flexible-server restore \
     --resource-group meeting-notes-summarizer \
     --name psql-meeting-notes-summarizer-restore-<yyyymmddhhmm> \
     --source-server psql-meeting-notes-summarizer \
     --restore-time "<YYYY-MM-DDTHH:MM:SSZ>"
   ```

3. Wait until the restore finishes:

   ```bash
   az postgres flexible-server show \
     --resource-group meeting-notes-summarizer \
     --name psql-meeting-notes-summarizer-restore-<yyyymmddhhmm> \
     --query state
   ```

   Expected value: `"Ready"`.
4. Set up a private endpoint and a private DNS record for the restored server,
   using the same settings as `azurerm_private_endpoint.postgresql_pe` in
   `infra/main.tf`.
5. Check the data (see "Verification" below).
6. Cut over by doing one of these:
   - Point the backend's database host setting at the restored server and
     redeploy, **or**
   - Use `pg_dump` / `pg_restore` to copy only the affected tables back into
     the primary server.
7. Update the Terraform state or config so it matches the server that is now
   in use. Remove the temporary server once the incident is closed.

## Procedure B: Geo-restore (regional outage)

```bash
az postgres flexible-server geo-restore \
  --resource-group meeting-notes-summarizer \
  --name psql-meeting-notes-summarizer-geo \
  --source-server psql-meeting-notes-summarizer \
  --location ukwest
```

Then do steps 3–7 from Procedure A, with networking set up in the `ukwest`
VNet. Expect to lose up to about 1 hour of data (Azure geo-backup RPO).

## Verification

Connect to the restored server with `psql` and check:

```sql
SELECT count(*) FROM meetings_meeting;
SELECT count(*) FROM meetings_actionitem;
SELECT max(created_at) FROM meetings_meeting;   -- should be just before the restore point
SELECT * FROM django_migrations ORDER BY id DESC LIMIT 5;
```

Run the backend against the restored server (`python manage.py migrate --check`).
Confirm that login and `GET /api/meetings/` both work.

## Restore test record

A restore test (Procedure A, followed by Verification) must be run **at least
once before go-live** and recorded below. After that, repeat it at least once
a year. Only add a row after the test has actually been run.

| Date (UTC) | Procedure | Restore point used | Restored server | Duration | Result / notes | Performed by |
|---|---|---|---|---|---|---|
| _pending: required before go-live_ | A (PITR) | | | | | |
