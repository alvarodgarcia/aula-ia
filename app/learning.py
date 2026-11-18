import random
import re
import unicodedata
from datetime import datetime
from fractions import Fraction
from zoneinfo import ZoneInfo


SCHOOL_TZ = ZoneInfo("Europe/Madrid")


def school_day() -> str:
    return datetime.now(SCHOOL_TZ).date().isoformat()


def math_operation(text: str) -> tuple[int, str, int] | None:
    match = re.fullmatch(r"\s*(?:¿Cuánto es\s+|Calcula\s+)?(\d{1,2})\s*([+−-])\s*(\d{1,2})\s*[?=.]?\s*", text, re.IGNORECASE)
    if match is None:
        return None
    left, operator, right = match.groups()
    return int(left), "+" if operator == "+" else "−", int(right)


def prefers_subtraction(topic: str) -> bool:
    return bool(re.search(r"\b(resta|restas|restar|sustracci[oó]n)\b", topic, re.IGNORECASE))


def requested_exercise_count(instructions: str) -> int:
    words = (
        "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
        "diez", "once", "doce", "trece", "catorce", "quince", "dieciseis", "diecisiete",
        "dieciocho", "diecinueve", "veinte",
    )
    counts = {word: value for value, word in enumerate(words)}
    counts.update({"un": 1, "una": 1})
    text = "".join(char for char in unicodedata.normalize("NFD", instructions.casefold())
                   if unicodedata.category(char) != "Mn")
    terms = "|".join(counts)
    match = re.search(rf"\b([0-9]{{1,8}}|{terms})\s+(?:ejercicios?|preguntas?|problemas?|actividades?)\b", text)
    if match is None:
        return 1
    amount = match.group(1)
    return int(amount) if amount.isdigit() else counts[amount]


def basic_drill(
    subtract: bool, level: int, *, different_from: tuple[int, str, int] | None = None,
) -> dict:
    if level == 0:
        left, right = random.randint(3, 9), random.randint(2, 6)
    elif level == 1:
        left, right = random.randint(12, 39), random.randint(3, 18)
    else:
        left, right = random.randint(28, 79), random.randint(12, 49)
    if subtract and left < right:
        left, right = right, left
    operator = "−" if subtract else "+"
    if (left, operator, right) == different_from:
        left += 1
    result = left - right if subtract else left + right
    hints = [
        "Mira qué operación aparece en el enunciado.",
        f"Empieza en {left} y cuenta {'hacia atrás' if subtract else 'hacia delante'}.",
        f"Separa {right} en decenas y unidades. Haz un cambio cada vez.",
    ]
    return {
        "subject": "Matemáticas",
        "topic": "Restas" if subtract else "Sumas",
        "difficulty": ("refuerzo", "adecuada", "reto")[level],
        "prompt": f"Calcula {left} {operator} {right}.",
        "answer_key": str(result),
        "worked_solution": f"Empieza en {left} y {'quita' if subtract else 'añade'} {right}. El resultado es {result}.",
        "hints": hints,
    }


def arithmetic_choices(answer: str) -> list[str]:
    result = int(answer)
    near = result - 1 if result > 0 else result + 1
    other = result - 10 if result >= 10 else result + 10
    return [answer, str(near), str(other)]


def option_identity(option: str) -> str | Fraction:
    text = " ".join(option.casefold().split()).replace("−", "-")
    numeric = text.replace(" ", "").replace(",", ".")
    if re.fullmatch(r"[+-]?(?:\d+(?:/\d+)?|\d*[.]\d+)%?", numeric):
        try:
            return Fraction(numeric.removesuffix("%")) / (100 if numeric.endswith("%") else 1)
        except (ValueError, ZeroDivisionError):
            pass
    return text


def answer_choices(raw: object, answer_key: str) -> list[str]:
    if not isinstance(raw, list) or len(raw) != 3:
        return []
    if any(type(option) not in (str, int, float) or not str(option).strip() or len(str(option).strip()) > 160 for option in raw):
        return []
    options = [str(option).strip() for option in raw]
    if answer_key not in options or len({option_identity(option) for option in options}) != 3:
        return []
    random.shuffle(options)
    return options


def pdf_page_text(text: str) -> dict[int, str]:
    parts = re.split(r"(?m)^\[P[áa]gina (\d+)\][ \t]*\r?\n?", text)
    pages = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}
    return pages or ({1: text.strip()} if text.strip() else {})


def selected_pdf_pages(text: str, first: int, last: int, *, page_limit: int = 8, source: str = "PDF") -> dict[int, str]:
    pages = pdf_page_text(text)
    if first < 1 or last < first or last - first >= page_limit or any(number not in pages for number in range(first, last + 1)):
        limit = "ocho" if page_limit == 8 else str(page_limit)
        raise ValueError(f"Elige hasta {limit} páginas conservadas en el texto del {source}.")
    selected = {number: pages[number][:2500] for number in range(first, last + 1)}
    if not any(selected.values()):
        raise ValueError("Las páginas seleccionadas no contienen texto. Revisa el OCR.")
    return selected
