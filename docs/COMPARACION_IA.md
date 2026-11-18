# Comparación de costes: OpenAI frente a modelo local

## Tarifa API de referencia

La configuración inicial usa gpt-6-luna: 0,10 USD por millón de tokens de entrada y 0,50 USD por millón de tokens de salida, según precios oficiales consultados el 16-11-2026. Son tarifas sujetas a cambio. ChatGPT Plus y el saldo de API se facturan por separado.

La app registra uso informado por el API y calcula un coste estimado desde las tarifas editables en .env. La factura puede variar por modelo, región, caché, créditos, impuestos y cambios de precio.

## Escenario ilustrativo de cuatro perfiles

Hipótesis: 4 alumnos, 3 sesiones por semana cada uno, 4,33 semanas por mes; 10 respuestas de tutor por sesión; 3.000 tokens de entrada y 600 de salida por respuesta; 1 ejercicio generado por sesión con 3.000 tokens de entrada y 700 de salida.

| Concepto | Tokens entrada | Tokens salida | Coste de referencia |
|---|---:|---:|---:|
| Tutor: 520 respuestas | 1.560.000 | 312.000 | 0,312 USD |
| Ejercicios: 52 | 156.000 | 36.400 | 0,033 USD |
| Total mensual aproximado | 1.716.000 | 348.400 | 0,3458 USD |

Con un modelo diez veces más caro, el mismo volumen sería aproximadamente 3,46 USD/mes antes de impuestos y conversión. El volumen real debe medirse en la app; los tokens por interacción dependen del contexto y de las respuestas.

## Energía local

Coste mensual = potencia durante inferencia en kW × horas de inferencia al mes × precio de electricidad en EUR/kWh.

Ejemplo: 250 W durante 8,7 horas al mes y 0,20 EUR/kWh = 0,44 EUR/mes. Si el PC se mantiene encendido solo para servir el tutor, suma también reposo: 80 W × 720 horas × 0,20 EUR/kWh = 11,52 EUR/mes. Son ejemplos, no mediciones de tu PC. Si ya está encendido para jugar, compara consumo con y sin inferencia para medir el incremento.

El cálculo no incluye coste de compra o actualización de GPU, depreciación, calor, ruido, mantenimiento ni disponibilidad. Sin modelo de GPU/VRAM y medición de potencia no se puede fijar un coste local exacto ni recomendar cuantización definitiva.

## Cómo probarlo

1. Ejecuta scripts/benchmark_ai.py con consultas ficticias en tres áreas.
2. Repite cinco veces y alterna el orden de proveedores.
3. Compara latencia y tokens; puntúa exactitud, claridad por curso, pista útil y revelación prematura de la solución.
4. Mide potencia en reposo e inferencia con un medidor o sensor de energía de Home Assistant.
5. Calcula coste OpenAI usando tokens reales y tarifas actuales; calcula local con kWh incrementales.
6. Compara coste por 100 ejercicios corregidos, latencia y calidad, no solo coste mensual.

## Decisión inicial

Para una familia, la API parece la forma más barata y sencilla de empezar, siempre que se mida el consumo real y se compruebe que el proveedor y la retención de datos encajan con el uso de PDFs escolares. Ollama es atractivo para experimentación y control local, pero puede exigir que el PC permanezca encendido y su calidad debe compararse en los ejercicios concretos. La app permite alternar el proveedor mediante AI_PROVIDER.
