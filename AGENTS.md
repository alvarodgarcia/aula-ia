# Trabajo en Aula IA

El usuario solicita que, a partir de la versión de referencia 1.0.0, cada mejora se incorpore como una nueva versión.

Excepción expresamente solicitada: la revisión de acento, naturalidad de voces y avisos de ruido/silencio es mantenimiento de 1.1.0, sin crear otra versión. Entregarla como parche de revisión; conservar las etiquetas y entregas ya publicadas.

El usuario autorizó probar Azure Speech F0 para corregir el acento usando voces regionales es-ES. Mantener OpenAI para tutor y transcripción; las claves se configuran en el servidor, nunca en el chat ni en el repositorio. Esta prueba continúa la revisión de voz de 1.1.0.

- Trabajar las mejoras en ramas `codex/<tema>` a partir del estado vigente; `main` es estable y `develop` prepara la siguiente entrega.
- Actualizar `VERSION` y `CHANGELOG.md` en cada nueva entrega. Usar versiones X.Y.Z: parche para correcciones, menor para funciones compatibles y mayor para cambios incompatibles.
- Incluir pruebas pertinentes y describir las comprobaciones realmente realizadas y sus límites. No afirmar que una revisión local certifica el servidor publicado.
- Mantener las capturas sin datos reales de alumnos. Nunca incluir `.env`, credenciales, bases de datos, adjuntos reales ni copias.
- Una mejora posterior requiere una nueva etiqueta y entrega; no sobrescribir las versiones publicadas. La autorización para publicar se determina por la petición vigente del usuario.

## Funcionamiento que debe conservarse

- El tutor es un profesor particular: explica, guía y propone práctica sin sustituir el razonamiento ni las lecturas del alumno. Conservar supervisión, historial y límites del adulto.
- Inglés usa el perfil y personaje existentes. La variedad en-GB/en-US, nivel y ayuda española se configuran por alumno. Mantener las firmas y cachés de voz por idioma.
- En Escucha, la nueva respuesta se reproduce tras solicitar la práctica. Los ejercicios creados en esta actividad guardan `EnglishExerciseContext`; su primera apertura en la sesión inicia la presentación inglesa, con detener/repetir y alternativa manual si el navegador bloquea el audio. No reproducir respuestas de referencia ni soluciones. No inferir la actividad de ejercicios antiguos.
- Pronunciación requiere activación familiar y permiso del alumno; audios de hasta 20 segundos, sin guardar la grabación, sin prosodia adicional y sin cambiar el plan Azure. Mantener reservas conservadoras y consumo de evaluación separado de caracteres de voz y tokens OpenAI.
- El menú del alumno contiene Inicio, Inglés, Apuntes/En clase y Repasos/Practicar. La subida de paquetes de fotos/PDF del alumno es para ESO y Bachillerato; el adulto supervisa los materiales.

## Instrucciones de uso y manual

- `/ayuda` sirve `app/guide/manual.html`; `/ayuda/pdf` sirve `app/guide/manual.pdf`. Mantener ambas versiones sincronizadas con los nombres y recorridos reales de la web, incluidas restricciones por perfil y configuración.
- Conservar las ilustraciones, accesibilidad, ejemplos y controles del manual. El progreso se guarda localmente en el navegador.
- Tras editar el HTML, ejecutar `node scripts/build_manual.mjs` con Node.js 22+ y Chrome/Chromium (`CHROME_PATH` opcional). Revisar capturas y páginas renderizadas del PDF; una generación correcta no sustituye la revisión visual.
- Actualizar también README y las guías relacionadas cuando cambie el funcionamiento. No dar a entender que un parche publicado ya está instalado en el servidor.

- Desde 1.5.0, Escucha usa `ListeningPreference` por alumno y `ListeningExercise` para separar pasaje privado y pregunta. La creación va por `/mis-tareas/ingles/listening`, con dificultad 1-3 relativa al MCER y duración acotada por edad. En modo solo audio, no enviar el pasaje al HTML/JSON del alumno ni a la generación de ayuda; el audio se sirve por ID con autorización. Mantener la pregunta visible, repetir y ayuda. Los modelos anteriores se conservan para compatibilidad con ejercicios históricos.
