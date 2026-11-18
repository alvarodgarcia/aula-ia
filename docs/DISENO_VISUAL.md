# Diseño visual de Aula IA

Esta actualización incorpora una identidad visual compartida para el acceso, el panel del adulto y las pantallas del alumno.

- Acceso ilustrado con los tutores, formularios claros y enlace al manual. En móvil, el formulario aparece primero.
- Cabecera del adulto con recuentos reales y enlaces a alumnos y materiales.
- Inicio del alumno con curso, progreso y siguiente tarea destacada.
- Colores cálidos en las primeras edades, verdes en Primaria y tonos más sobrios en ESO y Bachillerato.
- Tarjeta del tutor, ejercicios, apuntes y controles con tipografía, contraste y espaciado coherentes.
- Navegación por teclado, botones táctiles y respeto a la preferencia de movimiento reducido.

Los archivos se sirven desde la propia aplicación. Las tipografías Barlow incluyen sus licencias en `app/static/fonts`. La ilustración se reutiliza del manual de Aula IA.

## Aplicación

El parche es acumulativo sobre el parche «Cómo usar Aula IA». No contiene `.env`, datos del alumnado ni copias de seguridad. No requiere migraciones de base de datos ni cambios en BunkerWeb o NPMplus.

Subir el archivo a `/tmp/Aula_IA_parche_diseno_visual.tar.gz` y ejecutar desde la carpeta del proyecto:

```sh
cd /opt/proyecto-aula-ia &&
bash scripts/backup.sh &&
copia="backups/codigo-antes-diseno-$(date +%Y%m%d-%H%M%S)" &&
mkdir -p "$copia" &&
cp -a app requirements.txt Dockerfile "$copia/" &&
tar -xzf /tmp/Aula_IA_parche_diseno_visual.tar.gz &&
docker compose up -d --build --no-deps web &&
docker compose ps web
```

Después, recargar la página. Comprobar el acceso de alumno, su inicio, una tarea, el tutor y el panel de adulto. Las pruebas locales cubrieron anchos de 320, 390, 768, 1120 y 1280 píxeles, además de las interacciones de voz, tareas y materiales con respuestas de IA simuladas. La comprobación en la instalación publicada corresponde al momento de aplicar el parche.
