#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."

speech_region="${1:?Indica la región de tu recurso Speech F0, por ejemplo westeurope}"
if [[ ! "$speech_region" =~ ^[a-z0-9]{2,32}$ ]]; then
  echo "Indica solo el identificador de región, sin URL ni rutas." >&2
  exit 1
fi
test -f .env || { echo "No se ha encontrado .env en el proyecto." >&2; exit 1; }
echo "Usa la clave de un recurso Speech Free F0 que hayas creado en Azure."
echo "Este asistente no crea recursos ni contrata un nivel de pago."
IFS= read -r -s -p "Clave de Azure Speech (no se mostrará): " speech_key
speech_key="${speech_key%$'\r'}"
printf '\n'
if [[ ${#speech_key} -lt 16 || ${#speech_key} -gt 256 || ! "$speech_key" =~ ^[A-Za-z0-9+/=_-]+$ ]]; then
  echo "La clave tiene un formato no válido. No se ha modificado .env." >&2
  exit 1
fi
mkdir -p backups
env_copy="$(mktemp backups/env-antes-azure-XXXXXX)"
cp .env "$env_copy"
chmod 600 "$env_copy"
temporary="$(mktemp .env.azure.XXXXXX)"
trap 'rm -f "$temporary"' EXIT
awk '!/^(TUTOR_VOICE_PROVIDER|AZURE_SPEECH_KEY|AZURE_SPEECH_REGION)=/' .env > "$temporary"
{
  printf '\nTUTOR_VOICE_PROVIDER=azure\n'
  printf 'AZURE_SPEECH_REGION=%s\n' "$speech_region"
  printf 'AZURE_SPEECH_KEY=%s\n' "$speech_key"
} >> "$temporary"
chmod 600 "$temporary"
mv "$temporary" .env
unset speech_key
echo "Voz Azure configurada. Copia privada guardada en backups."
echo "Recrea web y abre Panel de adulto, Probar las voces del tutor."
