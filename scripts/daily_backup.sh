#!/usr/bin/env bash
# Template only. Configure and test with FSS IT before production use.
# Required environment: DB_NAME, DB_USER, DB_PASSWORD (prefer secret manager), GLPI_CONFIG_DIR, BACKUP_DIR
set -euo pipefail

: "${DB_NAME:?Set database name}"
: "${DB_USER:?Set database user}"
: "${DB_PASSWORD:?Use protected secret injection; do not hardcode}"
: "${GLPI_CONFIG_DIR:?Set GLPI configuration directory}"
: "${BACKUP_DIR:?Set protected off-host backup directory}"

RETENTION_DAYS="${RETENTION_DAYS:-30}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP="$BACKUP_DIR/.fss-glpi-$STAMP.tmp"
FINAL="$BACKUP_DIR/fss-glpi-$STAMP.tar.gz"
trap 'rm -f "$TMP"' EXIT

# Password is passed through MYSQL_PWD only for this process; a protected option
# file or managed secret is preferable in production. Ensure DB host/TLS policy
# is explicitly set by local operations standards.
export MYSQL_PWD="$DB_PASSWORD"
mysqldump --single-transaction --routines --triggers --user="$DB_USER" "$DB_NAME" > "$TMP"
unset MYSQL_PWD

# Archive DB dump and configuration together. Include additional GLPI data paths
# required by the deployment only after confirming consistency/retention policy.
tar -czf "$FINAL" -C "$BACKUP_DIR" "$(basename "$TMP")" -C "$(dirname "$GLPI_CONFIG_DIR")" "$(basename "$GLPI_CONFIG_DIR")"
rm -f "$TMP"
trap - EXIT
chmod 600 "$FINAL"
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'fss-glpi-*.tar.gz' -mtime "+$RETENTION_DAYS" -delete
printf 'Backup created: %s\n' "$FINAL"
# Production requirement: monitoring/alerting on non-zero exit and a scheduled
# isolated restore drill. Encrypt and replicate off-host per FSS policy.
