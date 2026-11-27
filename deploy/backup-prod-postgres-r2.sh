#!/usr/bin/env bash
set -euo pipefail

# Run from the production deployment directory. Keep backup credentials in the
# separate, mode-600 .backup.env file; do not put them in .env.prod.
backup_env="${BACKUP_ENV_FILE:-.backup.env}"
if [[ ! -r "$backup_env" ]]; then
  echo "Cannot read backup credentials file: $backup_env" >&2
  exit 1
fi

# The file is operator-managed and must not be writable by other users.
if [[ "$(stat -c '%a' "$backup_env")" != "600" ]]; then
  echo "Expected $backup_env permissions to be 600 (run chmod 600 $backup_env)" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$backup_env"
set +a

: "${BACKUP_R2_ACCOUNT_ID:?Set BACKUP_R2_ACCOUNT_ID in $backup_env}"
: "${BACKUP_R2_ACCESS_KEY_ID:?Set BACKUP_R2_ACCESS_KEY_ID in $backup_env}"
: "${BACKUP_R2_SECRET_ACCESS_KEY:?Set BACKUP_R2_SECRET_ACCESS_KEY in $backup_env}"
: "${BACKUP_R2_BUCKET:?Set BACKUP_R2_BUCKET in $backup_env}"
: "${BACKUP_AGE_RECIPIENT:?Set BACKUP_AGE_RECIPIENT in $backup_env}"

command -v docker >/dev/null
command -v age >/dev/null
command -v aws >/dev/null

export AWS_ACCESS_KEY_ID="$BACKUP_R2_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$BACKUP_R2_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION=auto
export AWS_EC2_METADATA_DISABLED=true

endpoint="https://${BACKUP_R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
object_key="postgres/${timestamp}.dump.age"

# IMAGE_TAG is only needed so Compose can parse the shared backend image field;
# exec uses the already-running database container and does not pull that image.
# Data streams through age directly to R2; no plaintext dump is written to disk.
IMAGE_TAG=backup-placeholder docker compose \
  -f compose.deploy.yml -f compose.prod.yml \
  exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" --format=custom "$POSTGRES_DB"' \
  | age -r "$BACKUP_AGE_RECIPIENT" \
  | aws s3 cp - "s3://${BACKUP_R2_BUCKET}/${object_key}" \
      --endpoint-url "$endpoint" --only-show-errors

aws s3api head-object \
  --bucket "$BACKUP_R2_BUCKET" \
  --key "$object_key" \
  --endpoint-url "$endpoint" >/dev/null

printf 'Encrypted PostgreSQL backup uploaded: s3://%s/%s\n' \
  "$BACKUP_R2_BUCKET" "$object_key"
