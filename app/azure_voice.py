"""Regional Azure Speech synthesis. Credentials are used only on the server."""
import io
import os
import re
import wave
from xml.sax.saxutils import escape

import httpx
from . import accounting


VOICES = {"lumo": "es-ES-ElviraNeural", "nora": "es-ES-XimenaNeural", "samir": "es-ES-AlvaroNeural"}
MAX_AUDIO_BYTES = 24000 * 2 * 100 + 4096


def region() -> str:
    value = os.getenv("AZURE_SPEECH_REGION", "").strip().lower()
    if not re.fullmatch(r"[a-z0-9]{2,32}", value):
        raise ValueError("Configura una región válida de Azure Speech")
    return value


def configured() -> bool:
    try:
        return bool(region() and os.getenv("AZURE_SPEECH_KEY", "").strip())
    except ValueError:
        return False


def ssml(text: str, character: str, age_group: str) -> str:
    speed = {"early": "-8%", "primary": "-3%", "teen": "0%"}[age_group]
    pitch = "+2%" if character == "lumo" else "0%"
    return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES">'
            f'<voice name="{VOICES[character]}"><prosody rate="{speed}" pitch="{pitch}">'
            f'{escape(text)}</prosody></voice></speak>')


def reserved_characters(text: str, character: str, age_group: str) -> int:
    # Conservative upper estimate, including markup and double-width/Unicode characters.
    return len(ssml(text, character, age_group).encode("utf-16-le"))


async def synthesize(text: str, character: str, age_group: str, key: str) -> bytes:
    event_id = accounting.begin("azure_voice", "azure", VOICES[character], "sintetizar",
                                text_characters=len(text), azure_units=reserved_characters(text, character, age_group))
    try:
        audio = await synthesize_audio(text, character, age_group, key)
        with wave.open(io.BytesIO(audio), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
        accounting.finish(event_id, audio_seconds=duration)
        return audio
    except Exception:
        accounting.fail(event_id)
        raise


async def synthesize_audio(text: str, character: str, age_group: str, key: str) -> bytes:
    endpoint = f"https://{region()}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
               "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm", "User-Agent": "AulaIA"}
    output = bytearray()
    async with httpx.AsyncClient(timeout=40, follow_redirects=False) as client:
        async with client.stream("POST", endpoint, headers=headers,
                                 content=ssml(text, character, age_group).encode()) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                output.extend(chunk)
                if len(output) > MAX_AUDIO_BYTES:
                    raise ValueError("Respuesta de voz demasiado larga")
    audio = bytes(output)
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000) or not wav.getnframes():
                raise ValueError("Formato de voz no válido")
            frames = wav.getnframes()
            if frames > 24000 * 100 or len(wav.readframes(frames)) != frames * 2:
                raise ValueError("Audio de voz incompleto o demasiado largo")
    except (wave.Error, EOFError) as exc:
        raise ValueError("La respuesta no contiene audio WAV válido") from exc
    return audio
