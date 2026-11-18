from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Preformatted, KeepTogether, ListFlowable, ListItem,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT = Path(__file__).resolve().parents[2] / "output" / "pdf" / "Informe_Tecnico_Aula_IA_Proxmox.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

pdfmetrics.registerFont(TTFont("LBSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("LBSans-Bold", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("LBMono", "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"))

INK = colors.HexColor("#182b40")
BLUE = colors.HexColor("#2463eb")
PALE = colors.HexColor("#eef4ff")
MINT = colors.HexColor("#e5f5ee")
GREY = colors.HexColor("#617286")
LINE = colors.HexColor("#dce4ee")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="LBSans-Bold", fontSize=27, leading=33, textColor=INK, alignment=TA_LEFT, spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontName="LBSans", fontSize=13, leading=19, textColor=GREY, spaceAfter=12))
styles.add(ParagraphStyle(name="eyebrow", parent=styles["Normal"], fontName="LBSans-Bold", fontSize=9, leading=12, textColor=BLUE, spaceAfter=4))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="LBSans-Bold", fontSize=17, leading=22, textColor=INK, spaceBefore=10, spaceAfter=8, keepWithNext=True))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="LBSans-Bold", fontSize=12, leading=16, textColor=BLUE, spaceBefore=8, spaceAfter=5, keepWithNext=True))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="LBSans", fontSize=9.3, leading=14, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontName="LBSans", fontSize=8, leading=11, textColor=GREY, spaceAfter=4))
styles.add(ParagraphStyle(name="Cellx", parent=styles["BodyText"], fontName="LBSans", fontSize=8, leading=10.5, textColor=INK))
styles.add(ParagraphStyle(name="CellHeadx", parent=styles["BodyText"], fontName="LBSans-Bold", fontSize=8, leading=10, textColor=colors.white))
styles.add(ParagraphStyle(name="Calloutx", parent=styles["BodyText"], fontName="LBSans-Bold", fontSize=10, leading=15, textColor=INK, leftIndent=8, rightIndent=8, spaceBefore=5, spaceAfter=7))
styles.add(ParagraphStyle(name="Codex", parent=styles["Code"], fontName="LBMono", fontSize=7.4, leading=10, textColor=INK, backColor=colors.HexColor("#f3f6fa"), borderColor=LINE, borderWidth=.5, borderPadding=7, leftIndent=6, rightIndent=6, spaceBefore=3, spaceAfter=8))
styles.add(ParagraphStyle(name="Linkx", parent=styles["BodyText"], fontName="LBSans", fontSize=8.2, leading=11, textColor=BLUE, spaceAfter=3))
styles.add(ParagraphStyle(name="Centerx", parent=styles["Normal"], fontName="LBSans", fontSize=9, leading=14, alignment=TA_CENTER, textColor=GREY))

def para(text, style="Bodyx"):
    return Paragraph(escape(text), styles[style])

def rich(text, style="Bodyx"):
    return Paragraph(text, styles[style])

def bullets(items):
    return ListFlowable(
        [ListItem(para(item), leftIndent=10) for item in items],
        bulletType="bullet", start="circle", leftIndent=16, bulletFontSize=6,
        bulletColor=BLUE, spaceAfter=5,
    )

def table(rows, widths, header=True):
    converted = []
    for ri, row in enumerate(rows):
        converted.append([
            Paragraph(escape(str(value)), styles["CellHeadx"] if header and ri == 0 else styles["Cellx"])
            for value in row
        ])
    t = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), .45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        commands.extend([("BACKGROUND", (0, 0), (-1, 0), INK), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE])])
    else:
        commands.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, PALE]))
    t.setStyle(TableStyle(commands))
    return t

def code(text):
    return Preformatted(text.strip(), styles["Codex"], maxLineLength=88, splitChars=" /.-")

def architecture_drawing():
    d = Drawing(500, 145)
    # Main nodes
    d.add(Rect(8, 46, 100, 55, rx=7, ry=7, fillColor=PALE, strokeColor=BLUE, strokeWidth=1))
    d.add(String(58, 79, "Navegador", textAnchor="middle", fontName="LBSans-Bold", fontSize=9, fillColor=INK))
    d.add(String(58, 63, "adulto / alumno", textAnchor="middle", fontName="LBSans", fontSize=8, fillColor=GREY))
    d.add(Rect(157, 31, 168, 84, rx=8, ry=8, fillColor=colors.HexColor("#f2f6fb"), strokeColor=INK, strokeWidth=1))
    d.add(String(241, 94, "VM Linux en Proxmox", textAnchor="middle", fontName="LBSans-Bold", fontSize=9, fillColor=INK))
    d.add(String(241, 76, "FastAPI + interfaz web", textAnchor="middle", fontName="LBSans", fontSize=8, fillColor=INK))
    d.add(String(241, 60, "PostgreSQL + PDFs / OCR", textAnchor="middle", fontName="LBSans", fontSize=8, fillColor=INK))
    d.add(String(241, 44, "Docker Compose", textAnchor="middle", fontName="LBSans", fontSize=8, fillColor=GREY))
    d.add(Rect(386, 83, 104, 43, rx=7, ry=7, fillColor=MINT, strokeColor=colors.HexColor("#318466"), strokeWidth=1))
    d.add(String(438, 108, "OpenAI API", textAnchor="middle", fontName="LBSans-Bold", fontSize=8.5, fillColor=INK))
    d.add(String(438, 94, "HTTPS / tokens", textAnchor="middle", fontName="LBSans", fontSize=7.5, fillColor=GREY))
    d.add(Rect(386, 23, 104, 43, rx=7, ry=7, fillColor=colors.HexColor("#fff3dc"), strokeColor=colors.HexColor("#bd8417"), strokeWidth=1))
    d.add(String(438, 48, "PC gaming", textAnchor="middle", fontName="LBSans-Bold", fontSize=8.5, fillColor=INK))
    d.add(String(438, 34, "Ollama local", textAnchor="middle", fontName="LBSans", fontSize=7.5, fillColor=GREY))
    # Connector lines and arrowheads
    d.add(Line(108, 74, 157, 74, strokeColor=BLUE, strokeWidth=1.5))
    d.add(Polygon([157,74,149,78,149,70], fillColor=BLUE, strokeColor=BLUE))
    d.add(Line(325, 83, 386, 103, strokeColor=BLUE, strokeWidth=1.5))
    d.add(Polygon([386,103,377,104,380,97], fillColor=BLUE, strokeColor=BLUE))
    d.add(Line(325, 59, 386, 45, strokeColor=BLUE, strokeWidth=1.5))
    d.add(Polygon([386,45,378,50,376,42], fillColor=BLUE, strokeColor=BLUE))
    d.add(String(352, 128, "Proveedor seleccionable", textAnchor="middle", fontName="LBSans", fontSize=7.5, fillColor=GREY))
    return d

def header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    if doc.page > 1:
        canvas.setStrokeColor(LINE)
        canvas.line(42, h - 34, w - 42, h - 34)
        canvas.setFont("LBSans-Bold", 8)
        canvas.setFillColor(INK)
        canvas.drawString(42, h - 26, "AULA IA")
        canvas.setFont("LBSans", 8)
        canvas.setFillColor(GREY)
        canvas.drawRightString(w - 42, h - 26, "Informe técnico · 16 noviembre 2026")
    canvas.setStrokeColor(LINE)
    canvas.line(42, 32, w - 42, 32)
    canvas.setFont("LBSans", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(42, 20, "Proyecto personal · MVP familiar · Costes estimados, no facturación medida")
    canvas.drawRightString(w - 42, 20, f"{doc.page}")
    canvas.restoreState()

story = []
story += [
    Spacer(1, 28*mm),
    para("PROYECTO PARA PROXMOX · VERSIÓN 0.1", "eyebrow"),
    Spacer(1, 5*mm),
    para("Aula IA: ejercicios escolares y tutor particular", "CoverTitle"),
    para("Informe técnico, despliegue y comparación económica entre OpenAI API y un modelo local en el PC gaming.", "CoverSub"),
    Spacer(1, 5*mm),
    table([
        ["Preparado", "Objetivo", "Estado"],
        ["16 de noviembre de 2026", "MVP para una familia", "Paquete listo para despliegue guiado"],
    ], [150, 170, 160]),
    Spacer(1, 7*mm),
    rich("<b>Recomendación inicial:</b> alojar la aplicación en una VM Linux independiente de Home Assistant y Jellyfin. Empezar con OpenAI API, registrar tokens reales y medir Ollama en el PC gaming antes de elegir el uso local como opción habitual.", "Calloutx"),
    Spacer(1, 3*mm),
    para("Este paquete incluye la aplicación MVP, los archivos de Docker Compose, el procedimiento de instalación, copia y recuperación, y un script para comparar respuestas sintéticas de ambos proveedores.", "Bodyx"),
    Spacer(1, 3*mm),
    para("No se ha instalado aún en Proxmox. Esta sesión no tiene conexión a tus nodos, credenciales API ni datos de GPU/consumo del PC gaming. Las cifras de coste local de este informe son ejemplos calculados con hipótesis editables.", "Smallx"),
    PageBreak(),
]

story += [
    para("1. Resumen ejecutivo", "H1x"),
    para("Aula IA permite crear perfiles de alumnos, elegir etapa, ciclo y curso, subir tareas PDF y practicar desde el navegador. El PDF se procesa localmente con extracción de texto y OCR en español; el adulto revisa la lectura antes de usarla. Hay dos flujos: generar práctica nueva y replicar el ejercicio indicado de una tarea escolar."),
    para("El tutor acompaña al alumno con pistas y explicación por edad/curso. Tras diez respuestas incorrectas aparece una reformulación breve de lo que pide y un primer paso; el alumno puede volver a intentarlo sin recibir la solución completa. Para respuestas abiertas, el proveedor IA juzga la respuesta con la solución y una rúbrica simple; matemáticas, física, unidades, OCR y ejercicios con diagramas requieren revisión humana."),
    bullets([
        "Aplicación desplegable con Docker Compose en una VM Linux; PostgreSQL y documentos persisten en volúmenes locales.",
        "La clave API se conserva en el servidor. La app registra tokens, latencia y coste estimado comunicado por el API.",
        "Ollama puede ejecutarse en el PC gaming, fuera de Proxmox, sin passthrough de GPU a la VM.",
        "Con el escenario familiar ilustrativo de cuatro perfiles, el coste de tokens con GPT-6 Luna sale aproximadamente a 0,35 USD al mes.",
        "Sin GPU, VRAM, consumo y tarifa eléctrica del PC gaming no se puede afirmar cuál proveedor será más barato en tu caso real."
    ]),
    para("2. Alcance funcional del MVP", "H1x"),
    table([
        ["Función", "Comportamiento previsto"],
        ["Perfil", "Nombre o alias, edad, etapa, ciclo y curso seleccionados de listas dependientes."],
        ["Etapas", "Infantil, Primaria, ESO y Bachillerato; ciclos/cursos en una configuración editable."],
        ["Tarea escolar", "Subir PDF, extraer/OCR, corregir el texto y replicar el ejercicio indicado por página o número."],
        ["Práctica", "Crear un ejercicio único por materia, tema y nivel a partir de un PDF o de un tema escrito."],
        ["Tutor", "Resolver dudas del ejercicio, dar pistas graduadas y explicar tras diez intentos."],
        ["Seguimiento", "Historial de ejercicios, intentos, tokens, coste API aproximado y latencia."],
        ["Acceso", "Una contraseña familiar de administración; primer uso restringido a LAN."],
    ], [112, 368]),
    para("Fuera de este primer alcance quedan cuentas separadas por alumno, roles, recuperación de contraseña, curriculum completo por comunidad autónoma, respuesta manuscrita, dibujos y evaluación matemática determinista.", "Smallx"),
    PageBreak(),
]

story += [
    para("3. Arquitectura y ubicación", "H1x"),
    architecture_drawing(),
    para("La VM debe convivir en el nodo que tenga memoria libre suficiente; no se fija un NUC concreto sin revisar la memoria y la carga actuales. Una asignación inicial de referencia es 2 vCPU, 4 GB RAM y 32 GB disco. Si el nodo está justo, prioriza continuidad de Home Assistant y Jellyfin y reduce la concurrencia OCR antes de asignar memoria que no esté libre.", "Bodyx"),
    table([
        ["Componente", "Ubicación", "Notas"],
        ["FastAPI + web", "VM Aula IA", "Puerto interno/published 8000; un solo proceso en el MVP."],
        ["PostgreSQL", "Contenedor Docker privado", "No publica puerto al host; datos en volumen Compose."],
        ["PDF y texto OCR", "VM, carpeta /opt/proyecto-aula-ia/data", "Persistencia local; copia fuera de la VM."],
        ["OpenAI", "Servicio externo HTTPS", "Solo envía contexto necesario para generar/corregir/tutor."],
        ["Ollama", "PC gaming en LAN", "API compatible OpenAI; puerto 11434 limitado a IP de VM."],
        ["Entrada externa", "BunkerWeb/NPMplus", "Opcional; activar TLS y acceso limitado después del piloto."],
    ], [95, 125, 260]),
    para("Por qué VM: separa el servicio del hipervisor y de HA/Jellyfin, hace sencillo instalar Docker y recuperar una copia de la máquina. La aplicación no necesita GPU si la inferencia se hace por OpenAI o en otro PC.", "Bodyx"),
    para("4. Modelo de datos y flujo", "H1x"),
    table([
        ["Entidad", "Datos principales"],
        ["Profile", "Alias, edad, etapa, ciclo y curso."],
        ["StudyDocument", "Perfil, nombre original, ruta del PDF, materia, tema y texto extraído revisable."],
        ["Exercise", "Perfil, documento fuente, modo replicar/practicar, enunciado, clave, solución, pistas y número de intentos."],
        ["Attempt", "Respuesta enviada, indicador correcto, comentario y fecha."],
        ["AIUsage", "Proveedor/modelo, tipo de petición, entrada/salida en tokens, coste estimado y latencia; no guarda el prompt."],
    ], [115, 365]),
    para("La app no envía el nombre del perfil al modelo. Envía edad aproximada, curso, materia, tema y el fragmento de contenido usado por la tarea. El OCR se ejecuta dentro de la VM; el texto extraído queda local hasta que se genera o se consulta un ejercicio.", "Bodyx"),
    PageBreak(),
]

story += [
    para("5. Proveedores IA y configuración", "H1x"),
    para("La aplicación usa el endpoint Chat Completions con formato compatible OpenAI. Para OpenAI se guarda una clave en el servidor. Para Ollama se cambia AI_PROVIDER y AI_BASE_URL; el código no necesita cambiar."),
    table([
        ["Variable", "OpenAI", "Ollama local"],
        ["AI_PROVIDER", "openai", "ollama"],
        ["AI_BASE_URL", "https://api.openai.com/v1", "http://IP_PC:11434/v1"],
        ["Clave", "OPENAI_API_KEY en .env", "AI_API_KEY=ollama (requerida por compatibilidad; no es secreto real)"],
        ["AI_MODEL", "gpt-6-luna", "Nombre exacto instalado, por ejemplo qwen3:8b"],
        ["Coste", "Tokens según tarifa y uso", "Sin coste por token; medir electricidad y disponibilidad"],
    ], [95, 185, 200]),
    para("No pongas la clave en JavaScript, HTML, el navegador ni el repositorio. La configuración de referencia registra 0,10 USD/M tokens de entrada y 0,50 USD/M tokens de salida para GPT-6 Luna, según la página de modelo consultada el 16-11-2026. Actualiza ambos valores antes de comparar una tarifa distinta.", "Bodyx"),
    para("La página oficial de Ollama lista Qwen3 8B Q4_K_M como una descarga de 5,2 GB. Ese tamaño de archivo no determina por sí solo la VRAM libre necesaria ni el rendimiento: se requiere el modelo exacto de GPU, VRAM y contexto para ajustar cuantización y concurrencia.", "Bodyx"),
    para("6. Comparación de coste", "H1x"),
    para("Escenario base ficticio para dimensionar, no consumo medido: cuatro perfiles, tres sesiones por semana cada uno, 4,33 semanas por mes; diez consultas al tutor por sesión; una tarea generada por sesión. Cada consulta usa 3.000 tokens de entrada y 600 de salida; cada ejercicio 3.000 de entrada y 700 de salida."),
    table([
        ["Uso", "Entradas/mes", "Salidas/mes", "Coste GPT-6 Luna"],
        ["Tutor: 520 respuestas", "1.560.000", "312.000", "0,312 USD"],
        ["Ejercicios: 52", "156.000", "36.400", "0,033 USD"],
        ["Total estimado", "1.716.000", "348.400", "0,3458 USD"],
    ], [165, 105, 100, 110]),
    para("Con GPT-6.1 Terra, cuya tarifa de entrada/salida es diez veces la de Luna en la consulta actual, el mismo volumen sería aproximadamente 3,46 USD/mes. Ambos importes son antes de impuestos/conversión y no incluyen servicios facturados por llamada o almacenamiento; el flujo MVP no usa búsqueda web ni almacenamiento de archivos del proveedor.", "Bodyx"),
    para("El cálculo local depende de la energía incremental. Fórmula: kWh/mes = potencia media en kW × horas de inferencia; coste = kWh × tarifa EUR/kWh.", "Bodyx"),
    table([
        ["Ejemplo hipotético", "Cálculo", "Coste orientativo"],
        ["PC durante inferencia", "0,25 kW × 8,7 h × 0,20 EUR/kWh", "0,44 EUR/mes"],
        ["PC dedicado 24/7 en reposo", "0,08 kW × 720 h × 0,20 EUR/kWh", "11,52 EUR/mes"],
    ], [150, 210, 120]),
    para("Los 250 W, 80 W, 8,7 horas y 0,20 EUR/kWh son parámetros de ejemplo. Si el PC ya se usa para jugar, mide solo el aumento respecto al consumo normal. Si hay que mantenerlo encendido exclusivamente para el tutor, incluye el reposo. La compra/ampliación de GPU, depreciación, calor, ruido y mantenimiento quedan fuera.", "Smallx"),
    PageBreak(),
]

story += [
    para("7. Benchmark reproducible", "H1x"),
    para("El paquete incorpora scripts/benchmark_ai.py. Usa tres consultas ficticias de matemáticas, lengua y física. No requiere subir PDFs reales ni usar nombres de alumnos. El script genera CSV con proveedor, modelo, latencia, tokens reportados y respuesta."),
    bullets([
        "Prepara las variables OPENAI_API_KEY, OPENAI_MODEL, LOCAL_BASE_URL y LOCAL_MODEL.",
        "Ejecuta la prueba cinco veces por proveedor y alterna el orden de ejecución.",
        "Puntúa a ciegas de 1 a 5: exactitud, lenguaje adecuado al curso, calidad de pista y respeto por no revelar pronto la respuesta.",
        "Mide el PC con un medidor de energía o sensor de Home Assistant: reposo, inferencia y consumo habitual con el juego en marcha.",
        "Calcula coste API con tokens observados y precios API vigentes; calcula local con kWh incrementales.",
        "Compara coste por 100 ejercicios, latencia y calidad. Guarda GPU, modelo, cuantización, temperatura y contexto para repetir la prueba."
    ]),
    para("No se ha ejecutado este benchmark: no hay clave API ni conexión con el PC gaming. El script y las hipótesis dejan preparado el ensayo; la tabla anterior es un cálculo, no un resultado experimental.", "Calloutx"),
    para("Decisión inicial sugerida", "H2x"),
    para("Comenzar con API permite mantener el PC gaming apagado y evita ajustar inferencia local. En el escenario familiar de referencia, el coste de tokens es bajo. Probar Ollama si interesa que documentos y prompts permanezcan dentro de la LAN, si se quiere aprender sobre modelos locales o si el equipo ya está encendido durante las sesiones. Mantener el selector de proveedor para poder volver a API cuando el PC no esté disponible.", "Bodyx"),
    para("8. Instalación en Proxmox: procedimiento", "H1x"),
    para("8.1 Preparar la VM", "H2x"),
    bullets([
        "Elegir el nodo con memoria libre suficiente; crear VM Linux independiente con IP fija/reserva DHCP.",
        "Punto de partida: 2 vCPU, 4 GB RAM, 32 GB disco. Confirmar uso real en Proxmox antes de asignar; mantener la VM fuera de cargas críticas si la memoria no alcanza.",
        "Habilitar firewall de VM en Proxmox. Permitir SSH desde administración y TCP 8000 solo desde LAN/proxy; no exponer el puerto PostgreSQL.",
        "Instalar Debian estable y aplicar actualizaciones. Docker recomienda instalar Engine desde su repositorio APT y ofrece Compose plugin en Debian."
    ]),
    para("8.2 Instalar Docker Engine y Compose en Debian", "H2x"),
    code("""sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $VERSION_CODENAME
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc" | sudo tee /etc/apt/sources.list.d/docker.sources
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl status docker
docker compose version"""),
    para("Si usas otra distribución Linux, sigue la página oficial equivalente. Docker advierte que los puertos publicados por contenedores pueden saltarse reglas de ufw/firewalld; conserva y verifica el filtrado a nivel de Proxmox y no confíes solo en ufw.", "Smallx"),
]

story += [
    para("9. Copia, secretos y puesta en marcha", "H1x"),
    para("9.1 Copiar y configurar el paquete", "H2x"),
    code("""sudo unzip Aula_IA_Proxmox.zip -d /opt
cd /opt/proyecto-aula-ia
cp .env.example .env
openssl rand -hex 32
openssl rand -hex 20
mkdir -p data/uploads backups
sudo chown -R 10001:10001 data
chmod 600 .env"""),
    para("Usa un secreto de sesión aleatorio de 32 bytes y una contraseña larga para la cuenta familiar. Para PostgreSQL, usa una contraseña hexadecimal generada con openssl rand -hex para evitar caracteres que haya que codificar en la URL. Sustituye la contraseña tanto en POSTGRES_PASSWORD como en DATABASE_URL.", "Bodyx"),
    para("9.2 Variables para OpenAI", "H2x"),
    code("""AI_PROVIDER=openai
AI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=clave_creada_en_API_platform
AI_MODEL=gpt-6-luna
AI_OPENAI_INPUT_USD_PER_MILLION=0.10
AI_OPENAI_OUTPUT_USD_PER_MILLION=0.50"""),
    para("ChatGPT y la plataforma API tienen facturación separada. Añade método de pago o créditos desde la cuenta API. Configura un límite/alerta de gasto en la plataforma si está disponible en tu organización.", "Bodyx"),
    para("9.3 Construir, iniciar y comprobar", "H2x"),
    code("""docker compose up -d --build
docker compose ps
docker compose logs -f web
curl http://127.0.0.1:8000/health"""),
    para("Abre http://IP_DE_LA_VM:8000 en la LAN. Inicia sesión con APP_ADMIN_PASSWORD. Crea un perfil, carga un PDF breve, corrige OCR y prueba primero generar una práctica ficticia. Revisa tokens/coste en el panel. Confirma el proxy solo después de la prueba local.", "Bodyx"),
    PageBreak(),
    para("9.4 Selección de Ollama en el PC gaming", "H2x"),
    bullets([
        "Instalar Ollama y descargar un modelo compatible con la GPU/VRAM. Qwen3 8B Q4_K_M sirve como referencia de prueba; su archivo ocupa alrededor de 5,2 GB.",
        "Configurar el servicio para aceptar conexiones en la interfaz LAN, no solo localhost. La forma exacta depende del sistema operativo instalado.",
        "En el firewall del PC, permitir TCP 11434 únicamente desde la IP de la VM. No abrirlo en router, DMZ, proxy público ni WAN.",
        "En .env cambiar AI_PROVIDER=ollama, AI_BASE_URL=http://IP_DEL_PC:11434/v1, AI_API_KEY=ollama y AI_MODEL al identificador exacto.",
        "Reiniciar con docker compose up -d y probar una tarea ficticia. Si el PC se apaga o duerme, el tutor local no estará disponible."
    ]),
    code("""AI_PROVIDER=ollama
AI_BASE_URL=http://192.168.1.50:11434/v1
AI_API_KEY=ollama
AI_MODEL=qwen3:8b"""),
    para("10. Publicación, autenticación y datos", "H1x"),
    bullets([
        "Mantener el piloto en LAN. El MVP usa una contraseña común familiar y no separa vistas por alumno.",
        "Para publicar después, dirigir DNS y proxy por BunkerWeb/NPMplus, activar TLS, limitar tasa y restringir TCP 8000 a la IP del proxy y LAN de administración.",
        "Activar APP_COOKIE_SECURE=true cuando toda la navegación use HTTPS.",
        "No publicar 5432/PostgreSQL ni 11434/Ollama; aplicar reglas en IPv4 e IPv6.",
        "La clave API solo vive en .env del servidor; guarda ese archivo con permisos restringidos y exclúyelo del ZIP/backup compartido.",
        "La guía de OpenAI indica que los datos API no se usan para entrenamiento por defecto. Los registros de supervisión de abuso pueden conservar contenido hasta 30 días por defecto. Comprueba la política vigente y limita el texto enviado.",
        "El OCR queda local. Cuando se llama al tutor, se envían edad/curso y el enunciado/contexto necesario; no se envía el nombre del perfil."
    ]),
    para("Esto no acredita cumplimiento legal para tratar datos de menores. Antes de facilitar cuentas fuera de la familia, añade autenticación individual, política de retención/borrado, controles de acceso y revisión especializada de privacidad.", "Smallx"),
    PageBreak(),
]

story += [
    para("11. Copias, actualización y recuperación", "H1x"),
    para("La aplicación necesita conservar conjuntamente la base de datos y data/uploads. El volumen de PostgreSQL está en Docker y los PDFs en /opt/proyecto-aula-ia/data. Ejecuta la copia y mueve los archivos a NAS u otro equipo; una copia dentro de la misma VM no protege frente a pérdida de disco."),
    code("""cd /opt/proyecto-aula-ia
bash scripts/backup.sh
ls -lh backups/"""),
    para("Restauración resumida: detén el servicio web; importa el archivo SQL con la base levantada; restaura data desde su tar; arranca y confirma perfiles/documentos. Practica restauración en una VM temporal antes de depender del sistema."),
    code("""docker compose stop web
gunzip -c aulaia-db-FECHA.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
tar -xzf aulaia-files-FECHA.tar.gz
docker compose up -d"""),
    para("Actualización: crea copia; cambia código/imagen a una versión revisada; reconstruye; inspecciona logs; conserva la copia anterior hasta confirmar la app. El MVP usa create_all y no incluye Alembic; no hagas cambios de esquema sobre una base en producción sin migración planificada.", "Bodyx"),
    para("12. Diagnóstico inicial", "H1x"),
    table([
        ["Síntoma", "Comprobaciones"],
        ["Web no responde", "VM IP, firewall TCP 8000, docker compose ps, logs de web."],
        ["Base no arranca", "POSTGRES_PASSWORD, DATABASE_URL y healthcheck de db."],
        ["PDF sin texto", "PDF borroso/protegido; número de páginas; Tesseract; corregir el OCR."],
        ["OpenAI falla", "Clave, facturación API, conectividad HTTPS, nombre de modelo, saldo/límites."],
        ["Ollama falla", "PC encendido, firewall TCP 11434 desde VM, dirección LAN y modelo instalado."],
        ["Coste parece cero", "Comprueba campo usage del proveedor; si no informa tokens, el estimador no puede calcularlos."],
        ["Subida falla", "Máximo 20 MB/40 páginas, disco libre y permiso UID 10001 en data."],
    ], [145, 335]),
    para("13. Límites y siguiente fase", "H1x"),
    bullets([
        "Añadir un campo para indicar número de ejercicio/página al replicar. Revisar que cifras y apartado coincidan con el PDF.",
        "Separar adulto/alumnos y añadir eliminación de perfil, exportación y política de retención.",
        "Usar banco de respuestas de matemáticas y evaluación determinista de números, fracciones, unidades y tolerancias.",
        "Añadir asignación/fecha de entrega, materias normalizadas, etiquetas curriculares y tablero de dominio por tema.",
        "Añadir cola de trabajos para OCR de PDFs largos y análisis paralelo, con límites por perfil.",
        "Revisar generaciones reales con padres/alumnos antes de usar resultados como nota."
    ]),
    PageBreak(),
    para("14. Fuentes consultadas", "H1x"),
    para("Precios y capacidades pueden cambiar. Consulta de referencia: 16 de noviembre de 2026.", "Smallx"),
]

sources = [
    ("OpenAI API: precio del modelo GPT-6 Luna", "https://developers.openai.com/api/docs/models/gpt-6-luna"),
    ("OpenAI API: tarifas", "https://developers.openai.com/api/docs/pricing"),
    ("OpenAI: controles de datos y retención", "https://developers.openai.com/api/docs/guides/your-data"),
    ("OpenAI: facturación separada ChatGPT/API", "https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform"),
    ("Docker: instalación oficial en Debian", "https://docs.docker.com/engine/install/debian/"),
    ("Docker: Compose plugin", "https://docs.docker.com/compose/install/linux/"),
    ("Docker: firewall y post-instalación", "https://docs.docker.com/engine/install/linux-postinstall/"),
    ("Ollama: compatibilidad OpenAI", "https://ollama.com/blog/openai-compatibility"),
    ("Ollama: Qwen3 8B Q4_K_M", "https://ollama.com/library/qwen3:8b"),
    ("Proxmox VE: guía y documentación", "https://www.proxmox.com/en/downloads/proxmox-virtual-environment/documentation"),
]
for label, url in sources:
    story.append(Paragraph(f'<link href="{escape(url)}" color="#2463eb">{escape(label)}</link><br/><font size="7" color="#617286">{escape(url)}</font>', styles["Linkx"]))

doc = SimpleDocTemplate(
    str(OUT), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=50, bottomMargin=42,
    title="Informe técnico Aula IA en Proxmox",
    author="OpenAI",
)
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(OUT)
