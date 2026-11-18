# Probar voces de España con Azure Speech F0

Esta prueba continúa la revisión de voz de Aula IA 1.1.0, sin nueva versión ni sustitución de las entregas publicadas. Azure se utiliza únicamente para leer en voz alta; las respuestas y la transcripción del micrófono siguen utilizando la configuración de OpenAI existente.

## 1. Crear el recurso gratuito

1. Acceder al [portal de Azure](https://portal.azure.com/) con una cuenta de Microsoft y completar el alta de Azure si es necesario.
2. Buscar **Speech** y crear un recurso de ese servicio. La presentación del portal puede referirse a Azure Speech o a Foundry Tools. No crear una máquina virtual, una voz personalizada ni un agente Voice Live para esta integración.
3. Elegir la suscripción disponible, un grupo de recursos nuevo para Aula IA y la región del recurso. Se puede usar **West Europe / Europa occidental** si ofrece el nivel gratuito y las voces seleccionadas.
4. En el nivel de precios, seleccionar **Free F0**. Comprobar el resumen antes de crear. Si F0 no aparece, detenerse y revisar las opciones; este procedimiento no necesita seleccionar S0/S1 ni un nivel de pago.
5. Cuando el recurso esté creado, abrir **Claves y punto de conexión** (o su equivalente en el portal) y localizar una clave y el identificador de región. Conservar la clave en privado. No enviarla al chat, GitHub ni capturas.

La aplicación no crea este recurso por su cuenta. La disponibilidad de F0 depende de la cuenta y región. El nivel F0 publica una cuota de 500.000 caracteres de voz neuronal al mes y tiene límites de peticiones. La cuota de este recurso se comparte con cualquier otra aplicación que utilice sus credenciales.

Referencias: [precios de Azure Speech](https://azure.microsoft.com/en-us/pricing/details/speech/), [voces e idiomas](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support), [API de síntesis](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech).

## 2. Instalar el parche acumulativo

Subir `Aula_IA_prueba_Azure_1.1.0.tar.gz` a `/tmp` en el servidor y ejecutar:

```sh
cd /opt/proyecto-aula-ia &&
bash scripts/backup.sh &&
copia="backups/codigo-antes-azure-$(date +%Y%m%d-%H%M%S)" &&
mkdir -p "$copia" &&
cp -a app requirements.txt Dockerfile docker-compose.yml scripts "$copia/" &&
if [ -f requirements.lock ]; then cp -a requirements.lock "$copia/"; fi &&
tar -xzf /tmp/Aula_IA_prueba_Azure_1.1.0.tar.gz &&
docker compose build --pull web
```

El parche contiene el proyecto completo acumulado, incluida la revisión de ruido/silencio y la privacidad. No contiene `.env`, claves, datos ni copias del alumnado. No necesita nuevas dependencias ni migraciones. Hasta configurar Azure se mantiene el proveedor anterior.

## 3. Configurar la clave sin mostrarla

En el mismo directorio, ejecutar el asistente con la región exacta del recurso. Ejemplo si se creó en Europa occidental:

```sh
bash scripts/configure_azure_voice.sh westeurope
```

Pegará la clave cuando el asistente la pida; no aparecerá en pantalla ni como argumento del comando. El asistente guarda una copia privada del `.env` anterior en `backups` y modifica solo `TUTOR_VOICE_PROVIDER`, `AZURE_SPEECH_REGION` y `AZURE_SPEECH_KEY`. Conserva las claves de OpenAI y la configuración del dominio, la base de datos y el proxy.

Después, recrear el servicio para que cargue el entorno actualizado:

```sh
docker compose up -d --no-deps web && docker compose ps web
```

## 4. Escuchar y comparar

Abrir Panel de adulto → **Probar las voces del tutor**. Elegir un alumno para adaptar el ritmo y escuchar Lumo, Nora y Samir:

| Personaje | Voz regional de Azure |
| --- | --- |
| Lumo | es-ES-ElviraNeural |
| Nora | es-ES-XimenaNeural |
| Samir | es-ES-AlvaroNeural |

La frase de prueba contiene «fíjate», «ejercicio», «cinco» y «doce» para apreciar la pronunciación. Las muestras son fijas, requieren acceso de adulto y no cambian el personaje del alumno. Se guardan en caché; pulsar de nuevo no debería generar otra llamada mientras exista el clip.

Después entrar como alumno, escuchar su saludo y probar una conversación. La reproducción indica **Azure Speech · España**. Si el proveedor falla, se permite únicamente un respaldo es-ES del dispositivo; si no existe se avisa en pantalla. No se cambia automáticamente a la síntesis de OpenAI.

## Límites de la prueba

- Se conserva el límite de nuevas generaciones por alumno y su pausa de IA.
- Azure tiene un límite local global de 18 solicitudes nuevas por ventana de 60 segundos y una reserva mensual conservadora de 400.000 unidades. Se cuentan texto y marcado con margen para Unicode; no es un contador exacto de caracteres facturados. Incluye las pruebas del adulto y las reservas de solicitudes que fallen. Solo cubre esta instalación, no otros usos de la clave.
- El mes se calcula en UTC y el contador persiste en la base de datos. El audio en caché de la base no vuelve a reservar unidades.
- F0 y la reserva local son controles distintos. No se puede comprobar el nivel contratado utilizando únicamente una clave de síntesis; el adulto debe confirmar F0 en el portal. Las alertas de presupuesto de Azure no sustituyen a la selección del nivel gratuito.
- Si una prueba falla, revisar clave, región, cuota y permisos del recurso. No copiar registros que contengan secretos al chat. Los mensajes de la aplicación no muestran la clave.

## Volver a OpenAI

Cambiar únicamente `TUTOR_VOICE_PROVIDER=openai` en `.env` y recrear web. No borrar ni sustituir el resto de variables. Las cachés de los dos proveedores tienen identificadores separados.

## Comprobaciones realizadas

Pruebas locales con proveedor simulado: selección de las tres voces es-ES, texto escapado en SSML, WAV válido, rechazo de respuestas incorrectas y de regiones no válidas, caché por proveedor, límite mensual antes de contactar al proveedor y prueba solo para el adulto con CSRF. Se conservan las regresiones de acceso, cuotas y conversación. El asistente de configuración se verifica con una clave ficticia en una carpeta temporal.

No se dispone todavía de un recurso F0 ni de una clave real del usuario, por lo que no se ha realizado una síntesis real en Azure ni una escucha de las voces. La instalación en el servidor y la calidad percibida se comprueban al completar los pasos anteriores. No se ha creado una cuenta o recurso de Azure ni contratado servicios en nombre del usuario.
