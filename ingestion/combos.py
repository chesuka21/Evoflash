"""Combo Detector — detecta 2 tarjetas Nivel 4 del mismo tema y sugiere fusión."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from vault_manager.vault_io import listar_pendientes, parse_flashcard, escribir_evolucion
from llm_interface.judge import LLMJudge
from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()
NIVEL_COMBO = 5  # Nivel 5: fusión (solo existe si dos N4 del mismo tema)


def buscar_combos() -> list[dict]:
    """Encuentra pares de tarjetas Nivel 4 del mismo tema para fusionar."""
    cards = listar_pendientes(settings.questions_dir())

    # Agrupar por tema+área y filtrar solo N4
    por_grupo = {}
    for c in cards:
        if c.nivel_actual < 4:
            continue
        key = f"{c.tema}|{c.area}"
        por_grupo.setdefault(key, []).append(c)

    # Solo parejas con 2+ tarjetas
    for (tema, area), grupo in por_grupo.items():
        if len(grupo) < 2:
            continue
        # Solo la primera pareja (la más antigua)
        a, b = grupo[0], grupo[1]
        combos.append({
            "tema": tema, "area": area,
            "tarjeta_a": {"id": a.id, "concepto": a.concepto, "pregunta": a.pregunta},
            "tarjeta_b": {"id": b.id, "concepto": b.concepto, "pregunta": b.pregunta},
        })
    return combos


def generar_combo(tema: str, area: str, cardA: dict, cardB: dict) -> dict:
    """Usa el LLM para crear una tarjeta combinada de Nivel 5."""
    prompt = f"""Eres un Motor de Aprendizaje Adaptativo EXPERTO.
Tienes dos tarjetas del Nivel 4 del mismo tema. Tu tarea: GENERAR una tarjeta de fusión (Nivel 5 — "combo").

REGLAS:
1. La pregunta debe integrar conceptos de AMBAS tarjetas en un solo problema.
2. El escenario debe ser más complejo que cualquiera de las dos por separado.
3. La respuesta esperada debe argumentar explícitamente por qué o cómo se vinculan ambos conceptos.
4. Formato: JSON válido con SOLO estos campos:
   {{
     "concepto": "nombre descriptiva del concepto fusionado",
     "pregunta": "...",
     "respuesta_esperada": "...",
     "nivel": 5,
     "es_combo": true
   }}

## Tarjeta A (Nivel 4)
Tema: {tema}
Concepto: {cardA['concepto']}
Pregunta: {cardA['pregunta']}

## Tarjeta B (Nivel 4)
Tema: {tema}
Concepto: {cardB['concepto']}
Pregunta: {cardB['pregunta']}

Genera el JSON. No salgas del formato."""
    j = LLMJudge()
    r = j.client.models.generate_content(
        model=settings.LLM_MODEL,
        contents=prompt,
        config=j._config(),
    )
    # Parsear JSON de la respuesta
    import json
    try:
        raw = "".join(p.text for p in r.candidates[0].content.parts if getattr(p, "text", None))
        return json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"LLM falló en combo: {e}")


def ejecutar_combos():
    """Detecta y ofrece crear una fusión por cada par de N4 del mismo tema."""
    combos = buscar_combos()
    if not combos:
        console.print("[yellow]📭 No tienes 2 tarjetas Nivel 4 del mismo tema para fusionar.[/yellow]")
        console.print("[dim](Sigue repasando hasta llegar a Nivel 4 en 2+ tarjetas del mismo tema)[/dim]")
        return

    console.print(f"[bold green]🔥 Encontré {len(combos)} potenciales combos:[/bold green]")
    for i, c in enumerate(combos, 1):
        console.print(f"\n{c['area']} | {c['tema']}")
        console.print(f"  A: {c['tarjeta_a']['concepto']}")
        console.print(f"  B: {c['tarjeta_b']['concepto']}")

    # Solo generar si el usuario quiero
    op = input("\n¿Generar combos? (s/n): ").strip().lower()
    if op != "s":
        return

    for c in combos:
        try:
            r = generar_combo(c['tema'], c['area'], c['tarjeta_a'], c['tarjeta_b'])
            # Crear tarjeta combo como nueva con nivel 5
            from datetime import date
            from pathlib import Path as _P
            cid = c['tema'].lower().replace(" ", "_")[:30] + f"_combo_{date.today().strftime('%m%d')}"
            path = settings.questions_dir() / f"{cid}.md"
            path.write_text(f"""---
id: {cid}
tema: {c['tema']}
concepto: {r['concepto']}
nivel_actual: {r['nivel']}
estado: activo
proximo_repaso: {date.today().isoformat()}
historial_aciertos: 0
fuente: "combo"
---

# Q: {r['pregunta']}
**A:** {r['respuesta_esperada']}

> [!combo] Este es un 🔥 Combo de nivel 5
> Fusión de: "{c['tarjeta_a']['concepto']}" + "{c['tarjeta_b']['concepto']}"
""", encoding="utf-8")
            console.print(f"[green]🌱 Combo creado: {path.name}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Error en combo '{c['tema']}': {e}[/red]")


if __name__ == "__main__":
    ejecutar_combos()
