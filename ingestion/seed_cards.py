"""Perfiles de estudio y decks — modo examen"""
from pathlib import Path
from datetime import date
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from vault_manager.vault_io import parse_flashcard


# ===== Perfil del estudiante (editable, no fijo) =====
PERFIL_DEFECTO = {
    "carrera": "Cybersecurity Analyst",
    "examenes_objetivo": ["Security+"],
    "idiomas": [],           # futuros decks (ej. "aleman")
    "intereses": [],         # temas libres
}


def perfil_path() -> Path:
    return settings.ROOT / "perfil_estudio.json"


def cargar_perfil() -> dict:
    import json
    if perfil_path().exists():
        return json.loads(perfil_path().read_text(encoding="utf-8"))
    return dict(PERFIL_DEFECTO)


def guardar_perfil(perfil: dict) -> None:
    import json
    perfil_path().write_text(json.dumps(perfil, indent=2, ensure_ascii=False), encoding="utf-8")


# ===== Generación de decks desde temario =====
PROMPT_TEMARIO = """Eres un generador de flashcards para preparar exámenes.

Perfil del estudiante: {perfil}
Examen/objetivo: {examen}
Temario (temas que pueden salir, separados por comas): {temario}
Nivel de dificultad solicitado: {nivel}

INSTRUCCIONES:
1. Genera 2-3 flashcards POR tema (no solo 1), para cubrir bien el temario.
2. 'tema' debe ser el nombre del área grande (ej. "Networking", "Criptografía").
3. 'concepto' es el subtema específico (ej. "Cifrado Simétrico").
4. Genera preguntas estilo examen {examen}: situaciones, opciones múltiples con distractor razonable, o respuestas cortas precisas según el caso.
5. Formato de respuesta: ÚNICAMENTE JSON válido:
[
  {{"tema": "...", "concepto": "...", "pregunta": "...", "respuesta_esperada": "...", "nivel": {nivel}}}
]
"""


def generar_deck(examen: str, temario: str, nivel: int = 1) -> list[dict]:
    """Llama al LLM y devuelve las flashcards generadas (sin escribir aún)."""
    import json
    from llm_interface.judge import LLMJudge
    j = LLMJudge()
    if j.mock:
        raise RuntimeError("Se necesita API key para generar decks (modo MOCK no genera temario).")

    from google.genai import types
    perfil = cargar_perfil()
    prompt = PROMPT_TEMARIO.format(
        perfil=json.dumps(perfil, ensure_ascii=False),
        examen=examen, temario=temario, nivel=nivel)
    r = j.client.models.generate_content(
        model=settings.LLM_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json",
                "temperature": 0.5},
    )
    try:
        raw = "".join(p.text for p in r.candidates[0].content.parts if getattr(p, "text", None))
    except (IndexError, AttributeError):
        raw = r.text or ""
    cards = json.loads(raw)
    assert isinstance(cards, list) and cards, "El LLM no devolvió lista de cards"
    return cards


def escribir_deck(cards: list[dict], subcarpeta: str | None = None) -> list[Path]:
    """Escribe las cards en el vault como notas .md (estructura EvoFlash)."""
    from vault_manager.vault_io import escribir_evolucion, parse_flashcard  # noqa: F401
    base = settings.vault_flashcards_dir()
    if subcarpeta:
        base = base / subcarpeta
    base.mkdir(parents=True, exist_ok=True)
    escritas = []
    for i, c in enumerate(cards, 1):
        cid = c.get("concepto", f"card_{i}").lower().replace(" ", "_")[:40]
        cid = f"{cid}_{i:03d}"
        path = base / f"{cid}.md"
        frontmatter = f"""---
id: {cid}
tema: {c.get("tema", "General")}
concepto: {c.get("concepto", "")}
nivel_actual: {int(c.get("nivel", 1))}
estado: activo
proximo_repaso: {date.today().isoformat()}
historial_aciertos: 0
---

# Q: {c.get("pregunta", "")}
**A:** {c.get("respuesta_esperada", "")}
"""
        path.write_text(frontmatter, encoding="utf-8")
        escritas.append(path)
    return escritas


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Generador de decks EvoFlash")
    ap.add_argument("--examen", required=True, help="Ej: 'Security+' o 'Examen final de Redes'")
    ap.add_argument("--temario", required=True, help="Temas separados por comas")
    ap.add_argument("--nivel", type=int, default=1)
    ap.add_argument("--subcarpeta", default=None, help="Subcarpeta dentro de EvoFlash/")
    args = ap.parse_args()
    cards = generar_deck(args.examen, args.temario, args.nivel)
    paths = escribir_deck(cards, args.subcarpeta)
    print(f"✅ Deck '{args.examen}': {len(paths)} tarjetas escritas en {paths[0].parent}")
    for p in paths:
        print(f"  - {p.name}")
