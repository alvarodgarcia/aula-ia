# Revisión de voz y conversación de 1.1.0

Mantenimiento solicitado sin una nueva versión. `VERSION` permanece en 1.1.0; las etiquetas y entregas ya publicadas se conservan. El código se publica en la rama `codex/revision-voz-conversacion` y se entrega en un parche acumulativo independiente.

## Cambios

- Las instrucciones de síntesis distinguen idioma y acento: español, castellano peninsular neutro. Se pide entonación conversacional, fluidez y pausas por significado, manteniendo el carácter de Lumo, Nora y Samir.
- El respaldo del navegador prioriza voces `es-ES` sobre otras variantes españolas y, dentro de esa selección, voces naturales. Se reducen las alteraciones de tono y la lentitud artificial. Su disponibilidad y calidad dependen del dispositivo.
- Se cambia el identificador del estilo de voz en las cachés del servidor y del saludo y se renuevan las referencias de los scripts. Los audios del estilo anterior dejan de reutilizarse para nuevas lecturas.
- A los 30 segundos aproximadamente de espera silenciosa, el tutor pregunta «¿Sigues por ahí?» sin prisa ni reproches. El aviso no reinicia el plazo de inactividad. A los dos minutos sin intervención se cierra el micrófono.
- Un sonido suficientemente fuerte y estable durante unos ocho segundos provoca un aviso para buscar tranquilidad o finalizar. Mientras continúa el sonido detectado, se suspende la grabación de turnos; el micrófono sigue activo para detectar cuándo baja. Tras medio segundo de tranquilidad se reanuda la grabación. Los avisos de ruido se espacian al menos 45 segundos y la espera prolongada termina cerrando el micrófono.
- El detector estima energía y variación de la señal. No identifica con certeza todos los ruidos ni distingue todas las voces ajenas. Se evita advertir solo porque el alumno lleve una explicación larga con variaciones normales de volumen.
- Los textos de aviso son fijos y llevan firma del servidor por perfil. La síntesis respeta sus controles y límites existentes. El análisis de ruido/silencio se realiza en el navegador; los fragmentos descartados no se envían a transcribir. La lectura de un aviso puede recurrir al proveedor de voz o al respaldo del dispositivo.

## Validación

Pruebas con reloj y micrófono simulados sobre el controlador real: toque de silencio, cierre por inactividad, aviso y espaciado ante ruido, descarte de turnos, recuperación al bajar el sonido, voz larga y cierre de la conversación durante un aviso. Pasaron también las cinco regresiones de seguridad, las regresiones generales y la conversación en navegador con dos turnos e interrupción al hablar. Los proveedores se simularon, sin gastar saldo.

No se ha escuchado una generación real del proveedor ni probado con el ruido físico del PC, tablet o móvil del usuario. El acento, naturalidad y sensibilidad requieren esa comprobación después de instalar. No se ha reconstruido Docker localmente ni modificado el servidor publicado.

## Aplicar

Subir `Aula_IA_revision_voz_1.1.0.tar.gz` a `/tmp` y ejecutar:

```sh
cd /opt/proyecto-aula-ia &&
bash scripts/backup.sh &&
copia="backups/codigo-antes-revision-voz-$(date +%Y%m%d-%H%M%S)" &&
mkdir -p "$copia" &&
cp -a app requirements.txt Dockerfile docker-compose.yml scripts "$copia/" &&
if [ -f requirements.lock ]; then cp -a requirements.lock "$copia/"; fi &&
tar -xzf /tmp/Aula_IA_revision_voz_1.1.0.tar.gz &&
docker compose build --pull web &&
docker compose up -d --no-deps web &&
docker compose ps web
```

Recargar la web y probar una lectura de cada personaje, una espera silenciosa y un sonido de fondo constante. Se conserva `.env` y no hay migraciones ni cambios de proveedor o modelo. El parche incluye el proyecto acumulado; no contiene datos del alumnado.
