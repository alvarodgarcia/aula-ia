# Trabajo en Aula IA

El usuario solicita que, a partir de la versión de referencia 1.0.0, cada mejora se incorpore como una nueva versión.

Excepción expresamente solicitada: la revisión de acento, naturalidad de voces y avisos de ruido/silencio es mantenimiento de 1.1.0, sin crear otra versión. Entregarla como parche de revisión; conservar las etiquetas y entregas ya publicadas.

- Trabajar las mejoras en ramas `codex/<tema>` a partir del estado vigente; `main` es estable y `develop` prepara la siguiente entrega.
- Actualizar `VERSION` y `CHANGELOG.md` en cada nueva entrega. Usar versiones X.Y.Z: parche para correcciones, menor para funciones compatibles y mayor para cambios incompatibles.
- Incluir pruebas pertinentes y describir las comprobaciones realmente realizadas y sus límites. No afirmar que una revisión local certifica el servidor publicado.
- Mantener las capturas sin datos reales de alumnos. Nunca incluir `.env`, credenciales, bases de datos, adjuntos reales ni copias.
- Una mejora posterior requiere una nueva etiqueta y entrega; no sobrescribir las versiones publicadas. La autorización para publicar se determina por la petición vigente del usuario.
