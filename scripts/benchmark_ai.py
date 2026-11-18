#!/usr/bin/env python3
"""Compara endpoints OpenAI-compatible usando preguntas ficticias y no personales."""
import csv
import os
import sys
import time
from datetime import datetime
import httpx

PROMPTS = [
    ("pista_matematicas", "Una alumna de 4.º de Primaria no sabe resolver 3/4 + 1/8. Dale una pista sin decir el resultado."),
    ("explicacion_lengua", "Explica qué es el sujeto de una oración para un alumno de 1.º de ESO, con un ejemplo."),
    ("razonamiento_fisica", "Un objeto recorre 120 metros en 20 segundos. Indica cómo calcular su velocidad media y qué unidad usar."),
]

def ask(provider, base_url, key, model, prompt_id, prompt):
    started = time.perf_counter()
    response = httpx.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": "Bearer " + (key or "ollama")},
        json={"model": model, "messages": [
            {"role": "system", "content": "Eres un tutor paciente. Responde en español claro y breve."},
            {"role": "user", "content": prompt}], "temperature": 0.2},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    usage = data.get("usage") or {}
    return {
        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "provider": provider, "model": model, "prompt_id": prompt_id,
        "latency_seconds": round(time.perf_counter() - started, 3),
        "input_tokens": usage.get("prompt_tokens", usage.get("input_tokens", "")),
        "output_tokens": usage.get("completion_tokens", usage.get("output_tokens", "")),
        "answer": data.get("choices", [{}])[0].get("message", {}).get("content", "").replace("\n", " "),
    }

def main():
    openai_key = os.getenv("OPENAI_API_KEY", "")
    local_base = os.getenv("LOCAL_BASE_URL", "")
    local_model = os.getenv("LOCAL_MODEL", "")
    if not openai_key or not local_base or not local_model:
        sys.exit("Define OPENAI_API_KEY, LOCAL_BASE_URL y LOCAL_MODEL.")
    endpoints = [
        ("openai", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), openai_key, os.getenv("OPENAI_MODEL", "gpt-6-luna")),
        ("local", local_base, "ollama", local_model),
    ]
    rows = []
    for prompt_id, prompt in PROMPTS:
        for name, base, key, model in endpoints:
            try:
                row = ask(name, base, key, model, prompt_id, prompt)
                rows.append(row)
                print(f"{name}/{model} · {prompt_id} · {row['latency_seconds']} s")
            except Exception as exc:
                print(f"ERROR {name}/{model} · {prompt_id}: {exc}", file=sys.stderr)
    out = os.getenv("BENCHMARK_CSV", "benchmark_results.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp_utc","provider","model","prompt_id","latency_seconds","input_tokens","output_tokens","answer"])
        writer.writeheader()
        writer.writerows(rows)
    print("Resultados guardados en " + out)

if __name__ == "__main__":
    main()
