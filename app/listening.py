"""Listening contracts: the pupil's question is separate from the private audio script."""
import re

DIFFICULTIES = {1: '1 · Paso a paso', 2: '2 · En contexto', 3: '3 · Reto'}
HELP = ('Read the question first. Are you listening for a person, a place, a time or a reason? '
        'Play the audio again and focus on that information. Try an answer in your own words. '
        'You do not need to understand every word.')


def word_range(level, age, difficulty):
    base = {'Por valorar': 18, 'Pre-A1': 18, 'A1': 24, 'A2': 35, 'B1': 48,
            'B2': 55, 'C1': 60, 'C2': 60}[level]
    # CEFR controls language; age bounds duration without inferring proficiency.
    base = min(base, 25 if age < 9 else 40 if age < 12 else 70)
    minimum = base * difficulty
    return minimum, min(210, minimum + max(10, base // 2))


def instruction(config, profile, difficulty):
    low, high = word_range(config['level'], profile.age, difficulty)
    return (
        f' Crea un listening original para {profile.age} años, curso {profile.course}, etapa {profile.stage}. '
        f'Dificultad relativa {difficulty}/3: {DIFFICULTIES[difficulty]}. '
        f'El texto tendrá entre {low} y {high} palabras y como máximo 1450 caracteres. '
        'El nivel 1 usa frases cortas y un dato explícito; el 2 conecta varios datos; '
        'el 3 amplía la narración y pide relacionar información, sin elevar el MCER configurado. '
        'En nivel Por valorar empieza con lenguaje muy sencillo. Adapta temas y madurez al curso. '
        'Devuelve JSON exclusivamente con decision="apoyo" si cumple las reglas escolares, passage (texto para oír), question (una pregunta de comprensión '
        'en inglés, hasta 220 caracteres, sin copiar la respuesta ni el pasaje), answer_key '
        '(respuesta de referencia), worked_solution (explicación privada). '
        'No añadas traducciones, HTML, Markdown ni la respuesta en question. '
    )


def parse(payload, config, profile, difficulty):
    if not isinstance(payload, dict):
        raise ValueError('No se recibió una actividad de escucha válida.')
    values = {}
    for key, maximum in (('passage', 1450), ('question', 220), ('answer_key', 400), ('worked_solution', 800)):
        text = payload.get(key)
        if not isinstance(text, str) or not text.strip() or len(text.strip()) > maximum:
            raise ValueError('La actividad no separó correctamente el audio y la pregunta. Prueba otra vez.')
        values[key] = text.strip()
    count = len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", values['passage']))
    low, high = word_range(config['level'], profile.age, difficulty)
    if not low <= count <= high:
        raise ValueError('La longitud no corresponde al nivel elegido. Prueba otra práctica.')
    if values['passage'].casefold() in values['question'].casefold():
        raise ValueError('La pregunta incluye el texto de escucha. Prueba otra práctica.')
    return values


def audio_text(passage, question):
    return "Listen carefully.\n\n" + passage + "\n\nNow answer the question. " + question
