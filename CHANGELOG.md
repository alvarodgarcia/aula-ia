# Cambios de Aula IA

## 1.4.1 · 2026-11-22

- Los ejercicios nuevos de Escucha conservan su actividad: el tutor presenta en inglés el enunciado y sus instrucciones al crearlos y al abrirlos por primera vez en la sesión, sin revelar la solución.
- Reproducción automática con detener/repetir y alternativa manual del navegador. Las recargas no repiten el audio ni generan nuevas consultas al tutor.
- Contexto de Escucha conservado al pedir ayuda dentro del ejercicio, límites de longitud para la locución y respeto de la pausa de Inglés. Tabla nueva `english_exercise_contexts` sin modificar columnas existentes.

## 1.4.0 · 2026-11-22

- Práctica de pronunciación básica con Azure Speech: frases guiadas, precisión, fluidez, lectura completada y resultados por palabra. Sonidos de referencia solo cuando Azure los devuelve para en-US. Sin prosodia ni cambio de plan del recurso.
- Grabación de hasta 20 segundos, conversión a WAV PCM en el navegador y validación real de formato/duración en el servidor. No se almacena el audio ni se duplica su transcripción en OpenAI.
- Activación del adulto y límites por familia/alumno. Reserva máxima familiar de 240 minutos mensuales; inicialmente 60 minutos y 10 intentos diarios por alumno. Las reservas inciertas se conservan ante errores.
- Escucha inicia el audio inglés al proponer una práctica, sin recargar la página cuando hay JavaScript. Permite detener y repetir; si el navegador bloquea el audio, ofrece reproducción manual. La recarga posterior no vuelve a iniciar el mismo turno.
- Monitor Azure con segundos de evaluación separados de caracteres de voz, historial de resultados y supervisión del adulto. Dos tablas nuevas sin alterar las columnas existentes.

## 1.3.0 · 2026-11-21

- Modo Inglés con conversación, gramática, vocabulario, lectura, escucha y escritura sobre el tutor y personaje existentes.
- Configuración del adulto por alumno: nivel orientativo independiente del curso, objetivo, variedad británica/americana y ayuda en español o solo inglés.
- Enseñanza especializada y autocorrección, aplicada también a ejercicios y repasos de inglés. Las ayudas en castellano se validan y guardan aparte de la respuesta inglesa.
- Seguimiento de turnos por habilidad, palabras practicadas y observaciones del tutor; visible al alumno y al adulto. No se asignan certificaciones ni se evalúa la pronunciación del audio.
- Voces Azure en en-GB/en-US, firmas y cachés por idioma y respaldo del dispositivo del mismo idioma. Se mantienen voces es-ES y límites/proveedores separados.
- Dos tablas nuevas; no se alteran las columnas de datos existentes ni las claves locales.

## 1.2.1 · 2026-11-18

- Separación completa de OpenAI y Azure en el panel de consumo y en el resumen del adulto: llamadas, cachés, detalle por alumno e históricos propios.
- El coste estimado de texto se muestra únicamente junto al proveedor que lo generó. Azure conserva sus caracteres, reservas y límite independiente.
- Se conservan los registros y presupuestos existentes. Los datos de otros proveedores, si existen, mantienen su sección propia.

## 1.2.0 · 2026-11-18

- Panel de adulto «Consumo y límites de IA», con filtros de periodo y alumno, totales y detalle de llamadas.
- Registro por perfil y actor de tokens comunicados, transcripciones, voz Azure y lecturas en caché. Los errores de contenido y las revisiones pedagógicas también se contabilizan.
- Presupuestos mensuales de tokens de texto para la familia y por alumno, con avisos al 80 %, 95 % y al alcanzar el presupuesto; bloqueo opcional mediante reservas previas y límites de salida.
- La reserva global de Azure sigue visible y activa. Se distinguen caracteres, tokens, duración comunicada y estimaciones, sin inferir el saldo del proveedor.
- Histórico previo conservado como consumo sin alumno asignado. Nuevas tablas de registro y presupuestos, sin alterar la estructura de los datos existentes.

## Prueba de voz Azure sobre 1.1.0 · 2026-11-18

- Proveedor de síntesis Azure Speech opcional con voces regionales es-ES: Elvira (Lumo), Ximena (Nora) y Álvaro (Samir). OpenAI conserva las respuestas y transcripciones.
- Prueba de los tres personajes desde el panel del adulto y visualización del origen de la voz durante la reproducción.
- Respaldo del navegador limitado a voces de España; si no hay ninguna instalada, se indica en pantalla en lugar de utilizar otra variante.
- Cachés separadas por proveedor, región, personaje y estilo. Límite mensual global conservador para la prueba y frecuencia local de generación.
- Asistente de configuración con clave oculta y copia privada de .env; información de privacidad actualizada para Azure.

## Revisión de 1.1.0 · Voz y conversación · 2026-11-18

Mantenimiento solicitado sin crear otra versión ni sustituir etiquetas o entregas publicadas.

- Instrucciones de voz más precisas para castellano peninsular y una entonación conversacional, manteniendo los personajes.
- Prioridad de voces es-ES y de voces naturales en la lectura de respaldo del navegador; menor alteración artificial del tono.
- Renovación de la caché de audio al cambiar el estilo, para no reutilizar la entonación anterior.
- Toque de voz tras unos 30 segundos de silencio, con cierre del micrófono a los dos minutos de inactividad.
- Aviso ante sonido fuerte y constante durante unos ocho segundos. Es una estimación de la señal, no un reconocimiento fiable de todos los tipos de ruido.
- Los avisos respetan los límites de síntesis existentes; el ruido detectado se descarta localmente en vez de enviarse como un turno.

## 1.1.0 · 2026-11-18

- Página pública «Privacidad y uso de IA», con información para alumnos y adulto sobre datos, supervisión, proveedores, conservación y eliminación en el ámbito familiar.
- Información sobre la cookie técnica propia, su duración y las comprobaciones pendientes de las cookies del proxy.
- Avisos antes de conversar por micrófono, dictar o subir fotos/PDF, con enlaces a la información ampliada.
- Identificación visible del tutor como IA también para las primeras edades.
- Enlaces permanentes a privacidad y cookies desde el pie de página. Sin herramientas de seguimiento ni nuevos registros de consentimiento.

## 1.0.0 · 2026-11-18

Primera versión de referencia en GitHub. Reúne las mejoras ya desarrolladas: tutor contextual y conversación por voz; perfiles por edad; tareas, notas y repasos por fechas; subida de paquetes de fotos y PDF; supervisión del adulto y límites de IA; manual interactivo/PDF y diseño visual adaptado.

Seguridad de esta entrega: límite independiente para transcripciones, cuota acumulada de adjuntos y frecuencia de subida, dependencias fijadas con huellas, recursos del contenedor limitados y copias con permisos privados.

Las capturas usan datos ficticios. Las pruebas nuevas y las regresiones locales pasaron. No se ejecutaron la reconstrucción Docker ni las comprobaciones OCR/PostgreSQL en esta última revisión, al no estar disponible Docker Desktop.
