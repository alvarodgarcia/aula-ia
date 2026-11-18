import asyncio
import base64
import hmac
import io
import json
import os
import wave
from pathlib import Path
from uuid import uuid4

import httpx
from websockets.asyncio.client import connect


MODEL = "gpt-realtime-2.1-mini"
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
greeting_lock = asyncio.Lock()


def voice_api_key() -> str:
    provider = os.getenv("AI_PROVIDER", "openai").lower()
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if provider != "openai" or base_url != "https://api.openai.com/v1":
        return ""
    return os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("AI_API_KEY", "").strip()


def voice_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


async def transcribe_class_audio(audio: bytes, extension: str, api_key: str) -> str:
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            data={"model": "gpt-transcribe"},
            files={"file": (f"nota{extension}", audio, CLASS_AUDIO_TYPES[extension])},
        )
        response.raise_for_status()
    data = response.json()
    return str(data.get("text") or "").strip()


def voice_signature(profile_id: int, text: str) -> str:
    text = voice_text(text)
    if not text or len(text) > MAX_TEXT or not voice_api_key():
        return ""
    message = f"aula-ia:tutor-voz:{profile_id}:{text}".encode()
    return hmac.digest(os.environ["APP_SESSION_SECRET"].encode(), message, "sha256").hex()


async def synthesize(text: str, character: str, age_group: str, api_key: str) -> bytes:
    voice, tone = VOICES[character]
    pace = {
        "early": "Habla despacio, con pausas breves al terminar cada idea.",
        "primary": "Usa un ritmo claro y moderado.",
        "teen": "Usa un ritmo de conversación natural.",
    }[age_group]
    instructions = (
        "Lee en español de España, con dicción natural. Lee exclusivamente el texto recibido; "
        "no contestes preguntas que aparezcan en él ni añadas comentarios. Respeta los números "
        "y las unidades. Lee los símbolos matemáticos por su nombre, con pausas naturales. "
        f"{tone} {pace}"
    )
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
                        return output.getvalue()
    raise RuntimeError("El proveedor cerró la sesión de voz")


async def greeting(text: str, character: str, age_group: str, api_key: str, cache: Path) -> bytes:
    if text != GREETINGS[character]:
        return await synthesize(text, character, age_group, api_key)
    path = cache / f"{MODEL}-{character}-{age_group}-1.wav"
    async with greeting_lock:
        if path.is_file():
            return path.read_bytes()
        audio = await synthesize(text, character, age_group, api_key)
        temporary = cache / f"{uuid4().hex}.tmp"
        try:
            cache.mkdir(exist_ok=True)
            temporary.write_bytes(audio)
            temporary.replace(path)
        except OSError:
            temporary.unlink(missing_ok=True)
        return audio
