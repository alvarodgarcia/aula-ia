# Instalación paso a paso en Proxmox

## 1. VM y red

1. Elige el nodo con RAM libre y crea una VM Linux independiente. Para iniciar, asigna 2 vCPU, 4 GB RAM y 32 GB de disco; revisa capacidad disponible antes de fijar recursos.
2. Asigna IP fija o reserva DHCP y DNS local.
3. Actualiza el sistema e instala Docker Engine y el plugin Docker Compose siguiendo la guía oficial de Docker para esa distribución.
4. Activa el firewall de Proxmox a nivel de VM. Permite SSH desde la red de administración y TCP 8000 desde LAN o desde la IP del proxy. No publiques 8000 en WAN.

## 2. Aplicación

1. Copia el ZIP a la VM y extráelo en /opt con `sudo unzip Aula_IA_Proxmox.zip -d /opt`.
2. Entra en `/opt/proyecto-aula-ia` y copia `.env.example` a `.env`.
3. Sustituye APP_SESSION_SECRET, APP_ADMIN_PASSWORD y POSTGRES_PASSWORD. Usa un secreto aleatorio de sesión de 32 caracteres o más. La contraseña de base de datos de DATABASE_URL debe coincidir exactamente.
4. Introduce OPENAI_API_KEY si vas a empezar con OpenAI. AI_MODEL se define por separado.
5. Crea directorios persistentes: mkdir -p data/uploads backups.
6. Asigna permisos: sudo chown -R 10001:10001 data.
7. Inicia: docker compose up -d --build.
8. Revisa: docker compose ps; docker compose logs -f web; curl http://127.0.0.1:8000/health.
9. Abre http://IP_DE_LA_VM:8000 desde la LAN, inicia sesión y crea un perfil.

## 3. Tareas PDF

Sube primero un PDF corto. El programa extrae texto localmente y aplica OCR en español cuando la página no tiene texto digital. Revisa y corrige el texto extraído antes de crear ejercicios. El límite inicial es 20 MB y 40 páginas.

## 4. Publicación opcional por proxy

Empieza en LAN. Para acceso exterior, crea el host en DNS y en el proxy existente; termina TLS en BunkerWeb/NPMplus, limita la tasa, mantén autenticación activa y restringe TCP 8000 a IPs de proxy y administración. Configura APP_COOKIE_SECURE=true cuando la app siempre esté servida bajo HTTPS. Revisa también IPv6. No publiques PostgreSQL ni Ollama.

## 5. PC gaming como proveedor local

1. Instala Ollama en Windows/Linux del PC.
2. Descarga un modelo que quepa en la VRAM disponible; anota modelo y cuantización.
3. Permite acceso de Ollama desde la LAN y crea regla de firewall TCP 11434 solo desde la IP de la VM.
4. En .env establece AI_PROVIDER=ollama, AI_BASE_URL=http://IP_DEL_PC:11434/v1, AI_API_KEY=ollama y AI_MODEL=nombre-exacto.
5. Reinicia la app con docker compose up -d. Verifica una tarea ficticia.

## 6. Copia y restauración

Ejecuta bash scripts/backup.sh. Copia los archivos de backups fuera de la VM, idealmente a otro equipo o NAS. Una copia local no protege frente a pérdida del disco.

Para recuperar: detén web, importa el SQL con gunzip -c ARCHIVO.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"', restaura el archivo tar sobre data y vuelve a arrancar docker compose up -d.

## 7. Operación

- Estado: docker compose ps
- Logs: docker compose logs -f web
- Reinicio: docker compose restart web
- Actualizar: haz copia, actualiza el código y reconstruye con docker compose up -d --build.
- Vigila espacio de disco, errores del proxy y crecimiento de PDFs.
- Guarda clave API solo en .env y limita permisos del archivo.
