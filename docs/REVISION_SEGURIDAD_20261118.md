# Revisión de seguridad · 18 de noviembre de 2026

Revisión local de Aula IA tras la actualización visual. Se inspeccionaron controles de sesión y CSRF, permisos de alumno y adulto, acceso a ejercicios y adjuntos, procesamiento de archivos, respuestas de IA, plantillas, scripts y configuración de despliegue. No se accedió al servidor publicado ni a datos reales de alumnos.

## Problemas corregidos

1. **Consumo de transcripciones sin límite al detectar silencio (riesgo medio).** La conversación devolvía el cupo pedagógico cuando la transcripción quedaba vacía, después de llamar al proveedor. Se incorpora un límite independiente, no reembolsable y compartido entre conversación y dictado: hasta tres veces el límite diario de IA del alumno por ventana de 24 horas. El silencio accidental sigue sin consumir el cupo pedagógico de la conversación. Una petición bloqueada no contacta con el proveedor.
2. **Acumulación ilimitada de adjuntos del alumnado (riesgo medio).** Se comprueba el espacio total por perfil antes del OCR y de nuevo antes de guardar, incluyendo todos los miembros de paquetes y los archivos retirados o bloqueados que conserva el adulto. La comprobación final usa un bloqueo del perfil en PostgreSQL. Por defecto, cada alumno dispone de 512 MB y puede intentar hasta 12 paquetes por ventana de una hora. Cada paquete conserva el límite de 20 archivos y 64 MB. El adulto puede eliminar materiales desde supervisión para liberar espacio.

## Dependencias y despliegue

- Versiones corregidas como mínimo para FastAPI, Starlette, python-multipart, Jinja y PyMuPDF.
- Nuevo `requirements.lock` con versiones exactas y huellas SHA-256. Docker instala con `--require-hashes`.
- Auditoría de los 36 paquetes resueltos para Linux/Python 3.12 con pip-audit: **0 vulnerabilidades conocidas** el 18 de noviembre de 2026. El resultado no cubre vulnerabilidades futuras ni paquetes del sistema operativo.
- Contenedor web limitado a 1536 MB, 2 CPU y 128 procesos, manteniendo usuario sin privilegios, sistema de archivos de solo lectura y capacidades eliminadas.
- Nuevas copias creadas con permisos privados. No se modifican los permisos de copias ya existentes.

Referencias contrastadas: [Starlette: límites de formularios](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq), [python-multipart: cabeceras sin límite](https://github.com/Kludex/python-multipart/security/advisories/GHSA-pp6c-gr5w-3c5g), [python-multipart: coste cuadrático](https://github.com/Kludex/python-multipart/security/advisories/GHSA-5rvq-cxj2-64vf).

## Validación

Las pruebas nuevas reprodujeron cuatro fallos de límites antes del cambio y pasaron después. También pasaron la conversación válida y el rechazo de CSRF incorrecto, las regresiones de tareas/tutor/repasos y el recorrido de interfaz en móvil, tablet y escritorio. Los proveedores de IA se simularon, sin gastar saldo. Se usaron SQLite y Python 3.13 en las pruebas locales; la semántica del bloqueo de PostgreSQL se revisó en el código. Las dependencias Linux se resolvieron y auditaron por separado.

Docker Desktop no estaba disponible: no se ejecutaron la reconstrucción Linux, el OCR con Tesseract ni un escáner de la imagen/paquetes Debian en esta revisión. Sigue siendo necesario validar el contenedor reconstruido en el servidor. Los límites del contenedor reducen el impacto de documentos costosos; no equivalen a aislar cada decodificador en un proceso con tiempo máximo individual.

## Aplicar el parche

El parche es acumulativo e incluye el diseño y el manual anteriores. No contiene `.env`, datos ni copias del alumnado. Subir a `/tmp/Aula_IA_parche_seguridad_v2.tar.gz` y ejecutar:

```sh
cd /opt/proyecto-aula-ia &&
bash scripts/backup.sh &&
copia="backups/codigo-antes-seguridad-v2-$(date +%Y%m%d-%H%M%S)" &&
mkdir -p "$copia" &&
cp -a app requirements.txt Dockerfile docker-compose.yml scripts "$copia/" &&
if [ -f requirements.lock ]; then cp -a requirements.lock "$copia/"; fi &&
tar -xzf /tmp/Aula_IA_parche_seguridad_v2.tar.gz &&
docker compose build --pull web &&
docker compose up -d --no-deps web &&
docker compose ps web
```

La reconstrucción descarga la imagen base actual y las dependencias fijadas. No requiere migraciones ni cambios del proxy. Comprobar después acceso de alumno/adulto, subida, tutor y `/health`. Los límites se aplican a nuevas solicitudes; los archivos existentes se conservan, aunque un alumno que ya supera su cuota no podrá añadir más hasta liberar espacio.

Las opciones `APP_STUDENT_STORAGE_MB` y `APP_STUDENT_UPLOADS_PER_HOUR` se pueden añadir a `.env`; si faltan, se usan 512 y 12. BunkerWeb y NPMplus deben seguir limitando cuerpos y accesos, respetando el protocolo HTTPS original y filtrando cabeceras de origen. El puerto 8000 solo debe aceptar conexiones del proxy y de administración, tanto en IPv4 como IPv6. Estos controles de red no se han verificado en el servidor.
