import asyncio
import base64
import hmac
import io
import json
import os
import wave
import hashlib
from pathlib import Path
from uuid import uuid4

import httpx
from websockets.asyncio.client import connect
from . import accounting, azure_voice


MODEL = "gpt-realtime-2.1-mini"
STYLE_REVISION = "es-ES-natural-2"
MAX_TEXT = 1800
MAX_CLASS_AUDIO = 8 * 1024 * 1024
CLASS_AUDIO_TYPES = {
    ".webm": "audio/webm", ".mp4": "audio/mp4", ".m4a": "audio/mp4", ".wav": "audio/wav",
    ".ogg": "audio/ogg", ".mp3": "audio/mpeg", ".flac": "audio/flac", ".mpeg": "audio/mpeg",
}
VOICES = {
    "lumo": ("coral", "Alegre, curioso y cercano. Sonríe al hablar y usa una entonación viva y natural, sin imitar una máquina."),
    "nora": ("marin", "Cálida, paciente y expresiva. Habla con calma, como una tutora que explica al lado del alumno."),
    "samir": ("cedar", "Sereno, cercano y directo. Destaca la idea principal con una entonación conversacional."),
}
GREETINGS = {
    "lumo": "¡Hola! Soy Lumo. ¿Qué vamos a descubrir hoy?",
    "nora": "¡Hola! Soy Nora. Cuando quieras, repasamos juntos lo que has dado en clase.",
    "samir": "Hola, soy Samir. ¿Qué te apetece practicar hoy?",
}
CONVERSATION_NOTICES = {
    "silence": "¿Sigues por ahí? Tómate tu tiempo. Cuando quieras, cuéntame qué estás pensando.",
    "noise": "Me cuesta distinguir tu voz del sonido de fondo. Busca un lugar más tranquilo o pulsa Finalizar conversación si prefieres seguir después.",
}
ENGLISH_GREETINGS = {
    "lumo": "Hello! I'm Lumo. Let's discover English together!",
    "nora": "Hello, I'm Nora. Let's practise English, one step at a time.",
    "samir": "Hi, I'm Samir. What would you like to practise today?",
}


def greetings(locale="es-ES"):
    return GREETINGS if locale == "es-ES" else ENGLISH_GREETINGS


greeting_lock = asyncio.Lock()


def provider() -> str:
    return os.getenv("TUTOR_VOICE_PROVIDER", "openai").strip().lower()


def provider_label() -> str:
    return {"openai": "OpenAI", "azure": "Azure Speech · España"}.get(provider(), "Proveedor no válido")


def synthesis_ready() -> bool:
    return azure_voice.configured() if provider() == "azure" else bool(voice_api_key()) if provider() == "openai" else False


def synthesis_key() -> str:
    return os.getenv("AZURE_SPEECH_KEY", "").strip() if provider() == "azure" else voice_api_key()


def cache_identity(character: str, locale: str = "es-ES") -> str:
    if locale != "es-ES":
        return f"{provider()}:{azure_voice.region() if provider() == 'azure' else MODEL}:{character}:{locale}:{STYLE_REVISION}"
    if provider() == "azure":
        return f"azure:{azure_voice.region()}:{azure_voice.VOICES[character]}:{STYLE_REVISION}"
    return f"openai:{MODEL}:{character}:{STYLE_REVISION}"


def voice_api_key() -> str:
    provider = os.getenv("AI_PROVIDER", "openai").lower()
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if provider != "openai" or base_url != "https://api.openai.com/v1":
        return ""
    return os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("AI_API_KEY", "").strip()


def voice_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


async def transcribe_class_audio(audio: bytes, extension: str, api_key: str) -> str:
    event_id = accounting.begin("transcription", "openai", "gpt-transcribe", "transcribir")
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data={"model": "gpt-transcribe"},
                files={"file": (f"nota{extension}", audio, CLASS_AUDIO_TYPES[extension])},
            )
            response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        duration = usage.get("seconds", data.get("duration")) if isinstance(usage, dict) else data.get("duration")
        accounting.finish(event_id, usage=usage, audio_seconds=duration)
    except Exception:
        accounting.fail(event_id)
        raise
    return str(data.get("text") or "").strip()


def voice_signature(profile_id: int, text: str, locale: str = "es-ES") -> str:
    text = voice_text(text)
    if locale not in {"es-ES", "en-GB", "en-US"} or not text or len(text) > MAX_TEXT or not synthesis_ready():
        return ""
    message = f"aula-ia:tutor-voz:{profile_id}:{text}".encode()
    if locale != "es-ES":
        message += f":locale:{locale}".encode()
    return hmac.digest(os.environ["APP_SESSION_SECRET"].encode(), message, "sha256").hex()


async def synthesize(text: str, character: str, age_group: str, api_key: str, locale: str = "es-ES") -> bytes:
    if provider() == "azure":
        return await azure_voice.synthesize(text, character, age_group, api_key, locale)
    if provider() != "openai":
        raise ValueError("Proveedor de voz no válido")
    event_id = accounting.begin("openai_voice", "openai", MODEL, "sintetizar", text_characters=len(text))
    try:
        return await synthesize_openai(text, character, age_group, api_key, event_id, locale)
    except Exception:
        accounting.fail(event_id)
        raise


async def synthesize_openai(text: str, character: str, age_group: str, api_key: str, event_id: str, locale: str = "es-ES") -> bytes:
    voice, tone = VOICES[character]
    pace = {
        "early": "Usa un ritmo tranquilo y cercano, con pausas cortas entre ideas; mantén las palabras fluidas, sin separar sílabas ni adoptar voz de bebé.",
        "primary": "Usa un ritmo conversacional claro, con pausas breves para comprender; evita la lentitud artificial.",
        "teen": "Usa un ritmo de conversación natural.",
    }[age_group]
    instructions = (
        "Idioma: español. Acento: castellano peninsular neutro de España, mantenido durante toda la lectura; "
        "distingue naturalmente la s de la z y de la c ante e/i, sin exagerarlo ni cambiar el texto. "
        "Suena como un profesor particular que conversa a tu lado: entonación variada y pausas según el sentido, "
        "enlaza las palabras con fluidez y termina las frases con naturalidad. Evita el tono de locución, "
        "la cadencia repetitiva, el canturreo y los cambios exagerados de tono. "
        "Lee exclusivamente el texto recibido; "
        "no contestes preguntas que aparezcan en él ni añadas comentarios. Respeta los números "
        "y las unidades. Lee los símbolos matemáticos por su nombre, con pausas naturales. "
        f"{tone} {pace}"
    )
    if locale != "es-ES":
        instructions = (f"Read only the supplied English text with a natural {'British' if locale == 'en-GB' else 'American'} English accent. Do not translate, add answers or comments. {tone} {pace}")
    event = {
        "type": "response.create",
        "response": {
            "conversation": "none",
            "output_modalities": ["audio"],
            "instructions": instructions,
            "audio": {"output": {"format": {"type": "audio/pcm", "rate": 24000}, "voice": voice}},
            "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]}],
        },
    }
    pcm = bytearray()
    async with asyncio.timeout(40):
        async with connect(
            f"wss://api.openai.com/v1/realtime?model={MODEL}",
            additional_headers={"Authorization": f"Bearer {api_key}"},
            open_timeout=8, close_timeout=2,
        ) as socket:
            ready = json.loads(await socket.recv())
            if ready["type"] != "session.created":
                raise RuntimeError("No se pudo iniciar la sesión de voz")
            await socket.send(json.dumps(event, ensure_ascii=False))
            async for message in socket:
                received = json.loads(message)
                if received["type"] == "response.output_audio.delta":
                    pcm.extend(base64.b64decode(received["delta"], validate=True))
                    if len(pcm) > 24000 * 2 * 100:
                        raise RuntimeError("Respuesta de voz demasiado larga")
                elif received["type"] == "error":
                    raise RuntimeError("El proveedor rechazó la petición de voz")
                elif received["type"] == "response.done":
                    if received["response"]["status"] != "completed" or not pcm or len(pcm) % 2:
                        raise RuntimeError("Respuesta de voz incompleta")
                    with io.BytesIO() as output:
                        with wave.open(output, "wb") as wav:
                            wav.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
                            wav.writeframes(pcm)
                        accounting.finish(event_id, usage=received["response"].get("usage"), audio_seconds=len(pcm) / 48000)
                        return output.getvalue()
    raise RuntimeError("El proveedor cerró la sesión de voz")


async def greeting(text: str, character: str, age_group: str, api_key: str, cache: Path, locale: str = "es-ES") -> bytes:
    if text != greetings(locale)[character]:
        return await synthesize(text, character, age_group, api_key, locale)
    identity = hashlib.sha256(cache_identity(character, locale).encode()).hexdigest()[:24]
    path = cache / f"{identity}-{character}-{age_group}.wav"
    async with greeting_lock:
        if path.is_file():
            accounting.cache_hit(provider(), MODEL if provider() == "openai" else azure_voice.selected_voice(character, locale))
            return path.read_bytes()
        audio = await synthesize(text, character, age_group, api_key, locale)
        temporary = cache / f"{uuid4().hex}.tmp"
        try:
            cache.mkdir(exist_ok=True)
            temporary.write_bytes(audio)
            temporary.replace(path)
        except OSError:
            temporary.unlink(missing_ok=True)
        return audio
