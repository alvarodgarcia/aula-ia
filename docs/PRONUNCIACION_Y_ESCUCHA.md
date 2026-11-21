# Pronunciación y Escucha · Aula IA 1.4.1

## Activar la pronunciación

El adulto entra en el panel principal, abre **Pronunciación** y activa la evaluación familiar. Después revisa la autorización y los límites de cada alumno. El alumno entra en **Inglés → Pronunciación**, elige una frase, escucha el ejemplo y pulsa **Grabar**. Al terminar, detiene la grabación para evaluarla. Cancelar antes del envío no solicita una evaluación.

La función familiar está desactivada inicialmente. Utiliza la clave y región del recurso Azure Speech ya configurado: para esta instalación, North Europe y F0. No cambia el nivel de precios, no crea recursos y no habilita la evaluación adicional de prosodia. Si Azure rechaza la petición, se muestra un aviso sin reintentar automáticamente.

Límites iniciales:

| Ámbito | Límite |
| --- | --- |
| Cada grabación | 20 segundos |
| Familia | 240 minutos por mes |
| Alumno | 60 minutos por mes y 10 intentos al día |

El adulto puede ajustar los límites de la aplicación, hasta 240 minutos mensuales y 30 intentos diarios por alumno. También se aplica el límite general de peticiones de IA del alumno. Los periodos se calculan en UTC. El límite familiar se comparte entre todos los alumnos y se reserva antes de contactar con Azure, incluso con peticiones simultáneas.

La reserva usa segundos redondeados hacia arriba. Un error o una respuesta no reconocida conserva la reserva y el intento: Azure podría haber procesado el audio. Un rechazo por límites de pronunciación, previo al envío, devuelve la reserva de la petición general de IA. El panel diferencia consumo confirmado y tiempo reservado; estos contadores locales no son una lectura del saldo de Azure.

El margen de 240 minutos es una precaución local, no una garantía de gratuidad: el recurso puede tener otros consumidores. Revisar sus cuotas y consumo en Azure antes de activarlo. La voz del ejemplo consume caracteres de síntesis por separado. No se cambia automáticamente a un plan de pago.

## Qué evalúa y qué conserva

Se envía a Azure únicamente un audio corto y la frase de referencia del catálogo del servidor. El navegador convierte la grabación a WAV PCM mono de 16 kHz y 16 bits; el servidor comprueba duración, formato y tamaño de nuevo. No se aceptan frases de referencia arbitrarias ni se guarda el audio en la base de datos o en archivos de la aplicación.

Se conservan alumno, fecha, frase, duración, estado y resultados filtrados para el seguimiento del adulto. Las puntuaciones de precisión, fluidez, completitud y resultado general aparecen solo si las devuelve Azure. Son orientativas, no una calificación oficial ni un diagnóstico. En inglés británico se presenta información por palabra; en inglés estadounidense también pueden mostrarse los sonidos de referencia devueltos por Azure. No se inventa una transcripción fonética de lo que ha pronunciado el alumno.

Esta evaluación no utiliza otra transcripción de OpenAI ni otra llamada al tutor para interpretar las puntuaciones. En **Consumo** se separan OpenAI, caracteres de voz Azure y segundos de evaluación Azure. La conversación habitual continúa funcionando como conversación y transcripción, sin atribuirle una evaluación fonética.

## Escucha más dinámica

En **Inglés → Escucha**, pulsar **Empezar una práctica** o enviar una pregunta prepara el nuevo turno y reproduce la respuesta en inglés automáticamente, sin recargar la página ni pulsar «leer». Se conservan la variedad británica o estadounidense y el personaje elegidos. El texto de escucha permanece plegado para practicar primero con el oído; puede desplegarse después.

Se puede detener el audio y volver a escucharlo. Algunos navegadores restringen la reproducción automática: si ocurre, aparece el aviso para pulsar el control de escucha. El micrófono no se abre por esta reproducción; para conversar por voz hay que activarlo expresamente. Al salir de la página o dejarla en segundo plano se detiene el audio. Recargar no reproduce automáticamente una respuesta antigua.

Desde 1.4.1, si se crea un ejercicio en Escucha, la respuesta hablada presenta en inglés el enunciado y las instrucciones para realizarlo. Al abrir ese ejercicio por primera vez en la sesión, el tutor inicia también esa presentación automáticamente. El mismo botón permite detenerla y volver a escucharla; las recargas y la revisión del adulto no la inician. No se leen la solución, las pistas ni la respuesta de referencia. Las preguntas al tutor dentro del ejercicio conservan la especialidad de Escucha.

Esto se aplica a los ejercicios creados desde esta revisión: los antiguos no conservaban su actividad de origen y no se reclasifican por suposición. Se crea la tabla `english_exercise_contexts`, sin alterar columnas existentes. Abrir el ejercicio no genera otra consulta de texto al tutor; la síntesis de voz mantiene sus límites y contabilidad habituales. La aplicación recuerda las últimas 20 aperturas de ejercicios de Escucha en la sesión para evitar repeticiones al recargar.

Sin JavaScript se mantiene el envío tradicional del formulario. La reproducción automática requiere JavaScript y un navegador compatible.

## Instalar el parche acumulativo

Subir `Aula_IA_parche_v1.4.1.tar.gz` a `/tmp` del servidor y ejecutar:

```sh
cd /opt/proyecto-aula-ia &&
bash scripts/backup.sh &&
copia="backups/codigo-antes-v1.4.1-$(date +%Y%m%d-%H%M%S)" &&
mkdir -p "$copia" &&
cp -a app requirements.txt Dockerfile docker-compose.yml scripts "$copia/" &&
if [ -f requirements.lock ]; then cp -a requirements.lock "$copia/"; fi &&
tar -xzf /tmp/Aula_IA_parche_v1.4.1.tar.gz &&
docker compose build --pull web &&
docker compose up -d --no-deps web &&
docker compose ps web
```

No se incluye ni se sobrescribe `.env`. Se crean las tablas `pronunciation_policies` y `pronunciation_attempts` al arrancar; no se alteran columnas anteriores. Conservar las copias y no restaurar una base antigua sin revisar las actividades posteriores. Volver al código previo deja estas tablas sin utilizar.

Tras instalar, probar una frase corta con un perfil de prueba y verificar el resultado y la atribución del consumo. Comprobar también Escucha en los móviles y tabletas de la familia.

## Comprobaciones y límites

![Pronunciación en móvil, con datos de prueba](screenshots/pronunciacion-movil-v1.4.png)

![Escucha automática en móvil, con datos de prueba](screenshots/escucha-automatica-v1.4.png)

Pruebas locales con SQLite y proveedores simulados: permisos, CSRF, aislamiento, formatos, límites compartidos simultáneos, errores sin reintentos, contabilidad separada, respuesta firmada y reproducción del nuevo turno una sola vez. Pruebas de navegador de reproducción automática, grabación, cancelación y visualización móvil.

No se ha desplegado esta versión en el servidor del usuario. No se ha realizado una petición facturable real a Azure ni se han comprobado su saldo F0, la calidad fonética real o PostgreSQL y Docker locales.

Referencias: [evaluación de pronunciación](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment), [API de audio corto](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short) y [precios de Speech](https://azure.microsoft.com/en-us/pricing/details/speech/).
