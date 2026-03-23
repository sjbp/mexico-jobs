"""
Score occupations for AI exposure using an LLM.

Reads output/occupations.json, sends each occupation description to Claude,
collects exposure scores (0-10) with rationales.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python score.py

Saves incrementally to output/scores.json (resumable).
"""

import json
import os
import time

try:
    import anthropic
except ImportError:
    print("Install the Anthropic SDK: pip install anthropic")
    exit(1)

BASE = os.path.dirname(os.path.abspath(__file__))

SCORING_PROMPT = """Eres un analista experto evaluando la exposición de distintas ocupaciones a la inteligencia artificial. Se te dará el nombre y código de una ocupación del Sistema Nacional de Clasificación de Ocupaciones (SINCO) de México.

Califica la exposición general de esta ocupación a la IA en una escala de 0 a 10.

La Exposición a IA mide: ¿cuánto va a transformar la IA esta ocupación? Considera tanto efectos directos (IA automatizando tareas que hacen humanos) como indirectos (IA haciendo a cada trabajador tan productivo que se necesitan menos).

Una señal clave es si el producto del trabajo es fundamentalmente digital. Si el trabajo puede hacerse completamente desde casa en una computadora — escribir, programar, analizar, comunicar — entonces la exposición a IA es inherentemente alta (7+), porque las capacidades de IA en dominios digitales avanzan rápidamente. Por el contrario, trabajos que requieren presencia física, habilidad manual, o interacción humana en tiempo real en el mundo físico tienen una barrera natural a la exposición a IA.

Usa estos puntos de referencia:

- 0–1: Exposición mínima. Trabajo casi enteramente físico, manual, o que requiere presencia humana en ambientes impredecibles. Ejemplos: albañil, agricultor, pescador.
- 2–3: Exposición baja. Mayormente trabajo físico o interpersonal. La IA puede ayudar con tareas periféricas menores pero no toca el trabajo central. Ejemplos: electricista, plomero, bombero.
- 4–5: Exposición moderada. Mezcla de trabajo físico/interpersonal y trabajo de conocimiento. La IA puede asistir significativamente con las partes de procesamiento de información. Ejemplos: enfermera, policía, veterinario.
- 6–7: Exposición alta. Predominantemente trabajo de conocimiento con cierta necesidad de juicio humano, relaciones o presencia física. Ejemplos: profesor, gerente, contador, periodista.
- 8–9: Exposición muy alta. El trabajo se hace casi enteramente en computadora. Todas las tareas centrales están en dominios donde la IA mejora rápidamente. Ejemplos: desarrollador de software, diseñador gráfico, traductor, analista de datos.
- 10: Exposición máxima. Procesamiento rutinario de información, completamente digital. Ejemplos: capturista de datos, telemarketer.

Responde SOLO con un objeto JSON en este formato exacto, sin otro texto:
{"exposure": <0-10>, "rationale": "<2-3 oraciones explicando los factores clave, en español>"}"""


def main():
    client = anthropic.Anthropic()

    with open(os.path.join(BASE, "output", "occupations.json"), encoding="utf-8") as f:
        occupations = json.load(f)

    # Load existing scores for resumability
    scores_path = os.path.join(BASE, "output", "scores.json")
    if os.path.exists(scores_path):
        with open(scores_path, encoding="utf-8") as f:
            scores = json.load(f)
    else:
        scores = []

    scored_codes = {s["sinco_code"] for s in scores}
    remaining = [o for o in occupations if o["sinco_code"] not in scored_codes]

    print(f"Total occupations: {len(occupations)}")
    print(f"Already scored: {len(scored_codes)}")
    print(f"Remaining: {len(remaining)}")

    for i, occ in enumerate(remaining):
        code = occ["sinco_code"]
        title = occ["title"]
        category = occ["category_es"]
        jobs = occ["jobs"]
        edu = occ["education_mode"]
        formality = occ["formality_rate"]

        user_msg = f"""Ocupación: {title}
Código SINCO: {code}
Categoría: {category}
Empleos en México: {jobs:,}
Educación típica: {edu}
Tasa de formalidad: {formality}%"""

        print(f"[{i+1}/{len(remaining)}] {code} {title[:60]}...", end=" ", flush=True)

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                messages=[
                    {"role": "user", "content": SCORING_PROMPT + "\n\n" + user_msg}
                ],
            )
            text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3].strip()
            result = json.loads(text)
            result["sinco_code"] = code
            result["title"] = title
            scores.append(result)
            print(f"-> {result['exposure']}/10")

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            # Try to extract from response
            result = {"sinco_code": code, "title": title, "exposure": None, "rationale": f"Parse error: {text[:100]}"}
            scores.append(result)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)
            continue

        # Save incrementally every 10 items
        if (i + 1) % 10 == 0:
            with open(scores_path, "w", encoding="utf-8") as f:
                json.dump(scores, f, ensure_ascii=False, indent=2)
            print(f"  [saved {len(scores)} scores]")

        # Rate limiting
        time.sleep(0.1)

    # Final save
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)
    print(f"\nDone! {len(scores)} scores saved to {scores_path}")
    print("Run build_site_data.py to rebuild site/data.json with scores.")


if __name__ == "__main__":
    main()
