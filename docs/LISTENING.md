# Listening con tres niveles · Aula IA 1.6.0

## Decisión del adulto por alumno

En **Panel de adulto → Perfiles de alumnos → Configurar → Profesor de inglés**, seleccionar **Texto de listening**:

- **Mostrar transcripción además del audio**: el alumno puede desplegar el texto para apoyarse en la lectura.
- **Solo audio: ocultar transcripción**: la pregunta sigue visible y se puede responder, pero el pasaje no se envía en el HTML ni en la respuesta JSON al alumno. La voz se solicita por el identificador del ejercicio, con comprobación del perfil y de la sesión.

Pulsar **Guardar inglés**. La opción afecta también a las actividades nuevas ya creadas, no solo a las siguientes. Inicialmente se conserva la opción de mostrar texto para no cambiar la configuración de las familias sin indicación. No puede retirarse lo que una persona ya haya leído, guardado u oído antes de cambiarla.

Los listening antiguos que mezclan pasaje y pregunta no pueden separarse con fiabilidad. Si el adulto oculta el texto, se invita a crear una actividad nueva en lugar de mostrar todo el enunciado. El historial antiguo de Escucha no se incluye en las páginas y contexto de conversación inglesa del alumno con ese ajuste.

## Recorrido del alumno

1. Entrar en **Inglés → Escucha**.
2. Elegir **1 · Paso a paso**, **2 · En contexto** o **3 · Reto**.
3. Pulsar **Empezar listening**. Se crea un ejercicio con el pasaje de audio separado de la pregunta. Al abrirlo por primera vez en la sesión, el tutor intenta iniciar la reproducción automáticamente.
4. Leer la pregunta, escuchar y escribir en **Tu respuesta**. Pulsar **Comprobar respuesta**.
5. Usar **Escuchar / repetir** para volver a oír el mismo audio; mientras suena, ese botón permite detenerlo. **Ayuda para responder** ofrece una estrategia sin resolver la pregunta.
6. Se puede escribir una duda concreta o conversar con el tutor para entender la pregunta o su vocabulario. Para otra actividad o dificultad, usar **Elegir otro nivel o práctica**.

Si el navegador bloquea el audio, pulsar el botón de escucha. No se abre el micrófono por reproducir: conversar por voz requiere activarlo. Las repeticiones pueden reutilizar el audio en caché; no generan una nueva consulta de creación de ejercicios. Cambiar de personaje puede necesitar otra síntesis de voz.

## Cómo se adaptan los niveles

Son tres dificultades relativas, no tres niveles MCER. Se conserva el inglés británico o americano y el nivel configurados por el adulto. El curso y la edad orientan los temas, la madurez y la duración, sin deducir la competencia lingüística de la edad.

| Dificultad | Propuesta |
| --- | --- |
| 1 · Paso a paso | Texto corto, frases sencillas y un dato explícito. |
| 2 · En contexto | Más extensión y varios datos que conectar. |
| 3 · Reto | El pasaje más amplio, con información que relacionar. |

El servidor exige un intervalo creciente de palabras para cada combinación de nivel y dificultad, con un tope de duración por edad y un máximo de 1450 caracteres de pasaje. Con nivel **Por valorar** se comienza con lenguaje sencillo. La generación tiene una sola oportunidad de reparación si no respeta longitud, separación o revisión de contenido; no se guarda una actividad inválida. La calidad lingüística real debe comprobarse en el uso.

## Ayuda, supervisión y consumo

Las pistas de estrategia no contienen el pasaje. Para explicar la pregunta, el tutor no recibe el texto privado en su solicitud de generación; una revisión separada puede consultarlo para comprobar que la ayuda no resuelve la actividad. Las peticiones de transcripción, traducción o respuesta se redirigen a la estrategia. No se pretende impedir que alguien transcriba por su cuenta un audio que puede escuchar, ni certificar un examen oficial.

La pregunta y el historial público se guardan separados del pasaje. Las correcciones mostradas al alumno no copian el texto privado. El adulto puede revisar la actividad desde su panel. Se mantienen límites de peticiones, presupuestos, permisos y atribución por alumno. Crear y corregir usan el proveedor de texto; el audio usa el proveedor de voz configurado. OpenAI y Azure conservan sus secciones de consumo separadas.

## Instalar y verificar

El parche acumulativo **Aula_IA_parche_v1.6.0.tar.gz** conserva `.env`, claves y región de Azure. Seguir los [pasos de instalación](PRONUNCIACION_Y_ESCUCHA.md#instalar-el-parche-acumulativo). Al arrancar se crean `listening_preferences` y `listening_exercises`, sin alterar columnas anteriores ni borrar datos.

Después de instalar, probar con un perfil de prueba: ocultar texto, generar una práctica, verificar pregunta/audio/respuesta, repetir y consultar ayuda. Volver al adulto, permitir el texto y comprobar la misma actividad. Probar cada dificultad y la voz en los dispositivos de la familia.

Pruebas locales con SQLite y proveedores simulados de permisos, aislamiento, CSRF, ajustes, longitud creciente, pausas/cuotas, caché, ayuda y contenido privado. Pruebas de navegador con cuatro tamaños, inicio de voz, detener/repetir y bloqueo de audio. No se ha desplegado en el servidor del usuario, reconstruido Docker local ni comprobado la calidad de una generación facturable real o PostgreSQL.
