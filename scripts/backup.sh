#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "backups/aulaia-db-$stamp.sql.gz"
tar -czf "backups/aulaia-files-$stamp.tar.gz" data
echo "Copia creada en backups con sufijo $stamp"
