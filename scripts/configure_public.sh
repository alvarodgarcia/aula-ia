#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
domain="${1:?Indica el dominio público, por ejemplo aula.ejemplo.es}"
proxy_ip="${2:?Indica la IP del proxy que se conecta a Aula IA}"
if [[ ! "$domain" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}$ ]] || [[ "$domain" == *..* ]]; then
  echo "El dominio debe escribirse sin https:// ni rutas." >&2
  exit 1
fi
if [[ ! "$proxy_ip" =~ ^[0-9a-fA-F:.]+$ ]]; then
  echo "Indica una sola dirección IP del proxy." >&2
  exit 1
fi
test -f .env
stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p backups
cp -p .env "backups/env-antes-internet-$stamp"
chmod 600 "backups/env-antes-internet-$stamp"
temporary="$(mktemp .env.public.XXXXXX)"
trap 'rm -f "$temporary"' EXIT
awk '!/^(APP_PUBLIC|APP_COOKIE_SECURE|APP_ALLOWED_HOSTS|FORWARDED_ALLOW_IPS)=/' .env > "$temporary"
{
  printf '\nAPP_PUBLIC=true\nAPP_COOKIE_SECURE=true\n'
  printf 'APP_ALLOWED_HOSTS=%s,localhost,127.0.0.1\n' "$domain"
  printf 'FORWARDED_ALLOW_IPS=%s\n' "$proxy_ip"
} >> "$temporary"
chmod 600 "$temporary"
mv "$temporary" .env
echo "Configuración guardada. Reconstruye web y accede por el dominio con HTTPS."
