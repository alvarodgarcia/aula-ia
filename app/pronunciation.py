"""Short, scripted Azure assessments. No prosody, audio storage or automatic retries."""
import base64
from datetime import datetime, timezone
import io
import json
import math
from uuid import uuid4
import wave

import httpx
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from . import accounting, azure_voice

MAX_SECONDS = 20
MAX_BYTES = 640_512
FAMILY_SECONDS = 240 * 60
PHRASES = {
    'hello': 'Hello! My name is Alex. I like playing with my friends.',
    'school': 'I go to school in the morning. My favourite subject is English.',
    'weekend': 'Last weekend I visited a friend. We played a game and had lunch together.',
    'plans': 'If the weather is nice tomorrow, we will go for a walk in the park.',
    'opinion': 'Learning a language takes patience. Making mistakes can help us understand what to practise next.',
    'choice': 'Although technology offers many opportunities, we should consider how our choices affect other people.',
}


class Base(DeclarativeBase):
    pass


class Policy(Base):
    __tablename__ = 'pronunciation_policies'
    scope_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    monthly_seconds: Mapped[int] = mapped_column(Integer, default=FAMILY_SECONDS)
    daily_attempts: Mapped[int] = mapped_column(Integer, default=10)


class Attempt(Base):
    __tablename__ = 'pronunciation_attempts'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    profile_id: Mapped[int] = mapped_column(Integer, index=True)
    locale: Mapped[str] = mapped_column(String(10))
    reference: Mapped[str] = mapped_column(String(300))
    seconds: Mapped[float] = mapped_column(Float)
    reserved_seconds: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default='pending')
    result: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class LimitReached(ValueError):
    pass


_factory = None


def configure(engine):
    global _factory
    _factory = sessionmaker(bind=engine, expire_on_commit=False)


def policy_data(policy, scope_id):
    return {'enabled': policy.enabled if policy else scope_id != 0,
            'monthly_seconds': policy.monthly_seconds if policy else FAMILY_SECONDS if scope_id == 0 else 3600,
            'daily_attempts': policy.daily_attempts if policy else 10}


def lock_policy(db, scope_id):
    if db.bind.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    defaults = policy_data(None, scope_id)
    db.execute(insert(Policy).values(scope_id=scope_id, **defaults).on_conflict_do_nothing(index_elements=['scope_id']))
    return db.get(Policy, scope_id, with_for_update=True)


def save_policy(scope_id, enabled, monthly_seconds, daily_attempts):
    with _factory() as db:
        policy = lock_policy(db, scope_id)
        policy.enabled, policy.monthly_seconds, policy.daily_attempts = enabled, monthly_seconds, daily_attempts
        db.commit()


def usage(db, scope_id=0):
    query = select(func.coalesce(func.sum(Attempt.reserved_seconds), 0)).where(Attempt.created_at >= accounting.month_start())
    if scope_id:
        query = query.where(Attempt.profile_id == scope_id)
    return int(db.scalar(query))


def overview(profile_id=0):
    with _factory() as db:
        family = policy_data(db.get(Policy, 0), 0)
        child = policy_data(db.get(Policy, profile_id), profile_id) if profile_id else None
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        attempts = db.scalars(select(Attempt).where(Attempt.profile_id == profile_id).order_by(Attempt.created_at.desc()).limit(10)).all() if profile_id else []
        daily = db.scalar(select(func.count()).select_from(Attempt).where(Attempt.profile_id == profile_id, Attempt.created_at >= today)) if profile_id else 0
        return {'family': family, 'child': child, 'family_used': usage(db), 'child_used': usage(db, profile_id) if profile_id else 0,
                'daily_used': daily, 'recent': [{'id': a.id, 'reference': a.reference, 'status': a.status,
                    'date': a.created_at, 'result': json.loads(a.result), 'seconds': a.reserved_seconds} for a in attempts]}


def reserve(profile_id, locale, reference, seconds):
    amount = math.ceil(seconds)
    with _factory() as db:
        family, child = lock_policy(db, 0), lock_policy(db, profile_id)
        if not family.enabled or not child.enabled:
            raise LimitReached('El adulto debe habilitar la práctica de pronunciación.')
        for scope_id, policy in ((0, family), (profile_id, child)):
            if usage(db, scope_id) + amount > policy.monthly_seconds:
                raise LimitReached('Se ha alcanzado el límite mensual local de pronunciación. Habla con el adulto.')
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        count = db.scalar(select(func.count()).select_from(Attempt).where(Attempt.profile_id == profile_id, Attempt.created_at >= today))
        if count >= child.daily_attempts:
            raise LimitReached('Has llegado al límite diario de prácticas de pronunciación.')
        attempt = Attempt(profile_id=profile_id, locale=locale, reference=reference, seconds=seconds, reserved_seconds=amount)
        db.add(attempt)
        db.commit()
        return attempt.id


def finish(attempt_id, result=None):
    with _factory() as db:
        attempt = db.get(Attempt, attempt_id, with_for_update=True)
        if attempt.status == 'pending':
            attempt.status = 'ok' if result is not None else 'error'
            attempt.result = json.dumps(result or {}, ensure_ascii=False)
            db.commit()


def canonical_audio(payload):
    if len(payload) > MAX_BYTES:
        raise ValueError('La grabación supera los 20 segundos permitidos.')
    try:
        with wave.open(io.BytesIO(payload), 'rb') as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, 'NONE'):
                raise ValueError('La grabación debe ser WAV PCM mono de 16 kHz y 16 bits.')
            frames = wav.getnframes()
            if not 1600 <= frames <= MAX_SECONDS * 16000:
                raise ValueError('Graba entre una décima de segundo y 20 segundos.')
            pcm = wav.readframes(frames)
            if len(pcm) != frames * 2:
                raise ValueError('La grabación está incompleta.')
    except (wave.Error, EOFError) as exc:
        raise ValueError('No se pudo leer la grabación WAV.') from exc
    # Rebuild headers: never forward extra user-supplied chunks to the provider.
    out = io.BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        wav.writeframes(pcm)
    return out.getvalue(), frames / 16000


def score(value):
    return round(float(value), 1) if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100 else None


def assessment_result(data, locale):
    if not isinstance(data, dict) or data.get('RecognitionStatus') != 'Success':
        raise ValueError('No se reconoció una lectura clara. Prueba con menos ruido y cerca del micrófono.')
    choices = data.get('NBest')
    item = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    metrics = item.get('PronunciationAssessment', item)
    if not isinstance(metrics, dict) or score(metrics.get('AccuracyScore')) is None:
        raise ValueError('Azure no devolvió una evaluación de pronunciación. Comprueba la disponibilidad en tu recurso.')
    result = {name: score(metrics.get(source)) for name, source in (
        ('accuracy', 'AccuracyScore'), ('fluency', 'FluencyScore'), ('completeness', 'CompletenessScore'), ('overall', 'PronScore'))}
    result['words'] = []
    words = item.get('Words')
    for word in (words if isinstance(words, list) else [])[:60]:
        if not isinstance(word, dict) or not isinstance(word.get('Word'), str):
            continue
        values = word.get('PronunciationAssessment', word)
        if not isinstance(values, dict):
            continue
        error = values.get('ErrorType', 'None')
        phonemes = word.get('Phonemes')
        sounds = []
        if locale == 'en-US' and isinstance(phonemes, list):
            for phoneme in phonemes[:20]:
                if not isinstance(phoneme, dict) or not isinstance(phoneme.get('Phoneme'), str) or not phoneme['Phoneme'].strip():
                    continue
                values_phoneme = phoneme.get('PronunciationAssessment', phoneme)
                if isinstance(values_phoneme, dict):
                    sounds.append({'name': phoneme['Phoneme'][:16], 'accuracy': score(values_phoneme.get('AccuracyScore'))})
        result['words'].append({'word': word['Word'][:80], 'accuracy': score(values.get('AccuracyScore')),
            'error': error if error in {'None', 'Omission', 'Insertion', 'Mispronunciation'} else 'None', 'sounds': sounds})
    # Do not infer spoken phonemes, IPA names, medical diagnoses or prosody.
    result['locale'] = locale
    return result


async def assess(audio, locale, reference):
    if locale not in {'en-GB', 'en-US'}:
        raise ValueError('Idioma de evaluación no válido.')
    import os
    parameters = {'ReferenceText': reference, 'GradingSystem': 'HundredMark', 'Granularity': 'Phoneme' if locale == 'en-US' else 'Word',
                  'Dimension': 'Comprehensive', 'EnableMiscue': True, 'EnableProsodyAssessment': False}
    headers = {'Ocp-Apim-Subscription-Key': os.environ['AZURE_SPEECH_KEY'],
        'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000',
        'Pronunciation-Assessment': base64.b64encode(json.dumps(parameters).encode()).decode()}
    endpoint = f'https://{azure_voice.region()}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1'
    output = bytearray()
    async with httpx.AsyncClient(timeout=35, follow_redirects=False) as client:
        async with client.stream('POST', endpoint, params={'language': locale, 'format': 'detailed'}, headers=headers, content=audio) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                output.extend(chunk)
                if len(output) > 1_000_000:
                    raise ValueError('La respuesta de evaluación es demasiado grande.')
    return assessment_result(json.loads(output), locale)
