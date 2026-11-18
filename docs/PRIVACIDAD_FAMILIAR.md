# Privacidad familiar · versión 1.1.0

Se incorpora `/privacidad`, accesible sin iniciar sesión y sin crear una cookie propia a un visitante nuevo. El pie de página enlaza a la información de privacidad y al apartado de cookies. Los avisos aparecen antes de la conversación por voz, el dictado y la selección de fotos/PDF. El tutor se identifica como IA también en las primeras edades.

El texto describe el uso exclusivamente familiar confirmado por el usuario. Explica la supervisión del adulto, OCR local, envío de contexto y audio al proveedor, conservación sin borrado automático general, diferencia entre retirar y eliminar un apunte y conservación independiente de las copias. No promete una configuración, plazo de borrado o ubicación del proveedor que no se haya verificado.

No se incorporan cookies de seguimiento, ventanas de consentimiento ni un registro adicional de aceptaciones. La página informa sobre la cookie propia `session`, sus 12 horas de duración renovable y el almacenamiento local de preferencias del tutor. La configuración de BunkerWeb/NPMplus y sus posibles cookies no se han inspeccionado. Si cambia el uso familiar o se añaden tecnologías de seguimiento, se deberá revisar la información y los requisitos aplicables.

Validación local: página accesible sin sesión sin crear cookie nueva, enlaces y anclas, cierre de sesión con CSRF, cinco regresiones de seguridad y recorrido de tareas/tutor. Diseño comprobado a 320, 390, 768 y 1120 píxeles y conversación por micrófono con proveedor simulado. No se ha aplicado ni certificado la instalación publicada; Docker Desktop no está disponible para reconstruir el contenedor localmente.

## Aplicar a una instalación existente

El archivo `Aula_IA_parche_v1.1.0.tar.gz` contiene el proyecto acumulado, incluida la actualización de seguridad 1.0.0. No incluye `.env` ni datos del alumnado. No requiere migraciones ni configurar nuevas variables.

Subir el archivo a `/tmp` y ejecutar:

```sh
cd /opt/proyecto-aula-ia &&
bash scripts/backup.sh &&
copia="backups/codigo-antes-v1.1.0-$(date +%Y%m%d-%H%M%S)" &&
mkdir -p "$copia" &&
cp -a app requirements.txt Dockerfile docker-compose.yml scripts "$copia/" &&
if [ -f requirements.lock ]; then cp -a requirements.lock "$copia/"; fi &&
tar -xzf /tmp/Aula_IA_parche_v1.1.0.tar.gz &&
docker compose build --pull web &&
docker compose up -d --no-deps web &&
docker compose ps web
```

Comprobar `/privacidad` sin sesión y los avisos en tutor, apuntes y subida de archivos. El administrador del servidor debe mantener el acceso limitado a la familia. La página no convierte esta instalación en un servicio abierto a terceros ni certifica su cumplimiento jurídico.
