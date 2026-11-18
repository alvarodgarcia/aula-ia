# Publicación de Aula IA

El parche crea un código individual para cada alumno con PIN. El adulto lo encuentra en Panel de adulto, Alumnos, nombre del alumno. El alumno utiliza código y PIN al entrar. Las sesiones previas del adulto deben iniciarse de nuevo después de aplicar este parche.

## Activar el modo público

Una vez preparado el dominio y el certificado HTTPS en el proxy, ejecuta desde el proyecto:

```bash
bash scripts/configure_public.sh aula.ejemplo.es IP_DEL_PROXY
docker compose up -d --build --no-deps web
```

Sustituye el dominio y la IP por los de tu instalación. En la cadena BunkerWeb → NPMplus → Aula IA, indica la IP de NPMplus que ve el contenedor y el subdominio de abgnetwork.es asignado a Aula IA. La configuración guarda una copia de .env en backups y activa cookies Secure, lista de dominios y confianza de cabeceras únicamente para esa IP. Conserva las claves y la configuración de IA existentes.

Configura el proxy para:

- Servir el dominio mediante HTTPS y redirigir HTTP a HTTPS.
- Enviar Host y sobrescribir X-Forwarded-For y X-Forwarded-Proto con los datos reales.
- Limitar el cuerpo a 66 MB y los accesos de inicio de sesión por IP.
- Permitir un tiempo de respuesta suficiente para el OCR de varios archivos.
- Restringir el acceso al puerto 8000 de la VM a la IP del proxy y a administración, también en IPv6.

Si BunkerWeb termina HTTPS y conecta por HTTP a NPMplus, configura NPMplus para conservar el protocolo HTTPS original solo en las conexiones que recibe de BunkerWeb. Restringe el acceso a NPMplus a las direcciones autorizadas. Conservar el dominio original en Host evita que la lista de dominios rechace peticiones legítimas. La aplicación debe confiar en NPMplus y NPMplus debe confiar únicamente en BunkerWeb al interpretar la IP real del navegador.

PostgreSQL y Ollama deben ser accesibles solo desde las redes autorizadas. .env y backups se guardan fuera de las rutas públicas. Configurar copias periódicas en otro equipo permite recuperar los apuntes.

## Comprobación desde fuera

Abre el dominio con un navegador sin sesión. La entrada del alumno pide código y PIN sin mostrar nombres ni cursos. Los adjuntos y el panel adulto requieren acceso autorizado.

En las herramientas del navegador comprueba que la cookie de sesión tiene Secure, HttpOnly y SameSite=Lax. Las cabeceras de respuesta deben incluir X-Frame-Options: DENY, X-Content-Type-Options: nosniff y Strict-Transport-Security.

La aplicación limita intentos de entrada y tamaños antes del análisis de formularios. La generación de voz se registra, reutiliza clips y respeta la pausa de IA. Un límite diario de N solicitudes permite hasta 3N generaciones de audio nuevas por cada ventana de 24 horas, además de la reutilización de clips.

La revisión del código se realizó sobre la copia local. La configuración del dominio, el proxy, el firewall y las dependencias del servidor debe verificarse en el despliegue.
