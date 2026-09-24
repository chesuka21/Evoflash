"""Exporta las flashcards a JSON para el Skill Tree visual."""
import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from vault_manager.vault_io import parse_flashcard
from datetime import date


def exportar() -> dict:
    cards = []
    questions = settings.questions_dir()
    for md in questions.rglob("*.md"):
        c = parse_flashcard(md)
        if c:
            cards.append({
                "id": c.id,
                "concepto": c.concepto,
                "tema": c.tema,
                "area": c.area,
                "nivel_actual": c.nivel_actual,
                "historial_aciertos": c.historial_aciertos,
                "estado": c.estado,
                "fuente": c.fuente,
                "es_boss": c.es_boss_battle,
                "es_practice": bool(c.practice_cmd),  # nombre consistente con HTML
                "path": str(md.relative_to(questions)),
            })
    return {"cards": cards, "fecha": date.today().isoformat()}


if __name__ == "__main__":
    data = exportar()
    out = settings.ROOT / "web_dashboard" / "data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {len(data['cards'])} tarjetas exportadas a {out}")
