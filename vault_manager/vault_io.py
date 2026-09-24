"""Vault I/O — lee/escribe flashcards en Obsidian (Markdown + YAML frontmatter)"""
import re
import yaml
from pathlib import Path
from datetime import date
from core_engine.flashcard import Flashcard


def parse_flashcard(md_path: Path) -> Flashcard | None:
    """Lee un .md con frontmatter YAML + cuerpo markdown -> Flashcard"""
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Frontmatter
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not m:
        return None
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    body = m.group(2)

    # Extraer Q y A del cuerpo
    q_match = re.search(r"# Q:\s*(.+)", body)
    a_match = re.search(r"\*\*A:\*\*\s*(.+)", body)
    pregunta = q_match.group(1).strip() if q_match else ""
    respuesta = a_match.group(1).strip() if a_match else ""

    return Flashcard(
        id=str(meta.get("id", md_path.stem)),
        tema=str(meta.get("tema", "General")),
        concepto=str(meta.get("concepto", "")),
        nivel_actual=int(meta.get("nivel_actual", 1)),
        estado=str(meta.get("estado", "activo")),
        proximo_repaso=_parse_date(meta.get("proximo_repaso")),
        historial_aciertos=int(meta.get("historial_aciertos", 0)),
        pregunta=pregunta,
        respuesta=respuesta,
        path=str(md_path),
    # Campos nuevos (opcionales)
        practice_cmd=str(meta.get("practice_cmd", "")),
        practice_esperada=str(meta.get("practice_esperada", "")),
        imagen_pregunta=str(meta.get("imagen_pregunta", "")),
        imagen_respuesta=str(meta.get("imagen_respuesta", "")),
        carpeta=md_path.parent.name,  # subcarpeta dentro de Questions/
        fuente=str(meta.get("fuente", "")),  # ruta original del apunte
    )


def _parse_date(v) -> date:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v)
        except ValueError:
            pass
    return date.today()


def escribir_evolucion(card: Flashcard, nueva_pregunta: str, nueva_respuesta: str,
                       nuevo_nivel: int, feedback: str) -> None:
    """Regenera el archivo .md con la evolución aplicada (modo atómico). Preserva campos nuevos."""
    path = Path(card.path)
    campos_extra = ""
    if card.practice_cmd:
        campos_extra += f"practice_cmd: {card.practice_cmd}\n"
    if card.practice_esperada:
        campos_extra += f"practice_esperada: {card.practice_esperada}\n"
    if card.imagen_pregunta:
        campos_extra += f"imagen_pregunta: {card.imagen_pregunta}\n"
    if card.imagen_respuesta:
        campos_extra += f"imagen_respuesta: {card.imagen_respuesta}\n"
    if card.fuente:
        campos_extra += f'fuente: "{card.fuente}"\n'

    contenido = f"""---
id: {card.id}
tema: {card.tema}
concepto: {card.concepto}
nivel_actual: {nuevo_nivel}
estado: {card.estado}
proximo_repaso: {card.proximo_repaso.isoformat()}
historial_aciertos: {card.historial_aciertos}
{campos_extra}---

# Q: {nueva_pregunta}
**A:** {nueva_respuesta}

***
> [!success] Evolución aplicada (Nivel {nuevo_nivel})
> {feedback}

> [!history] Historial
> - Nivel previo {card.nivel_actual}: "{card.pregunta}"
"""
    path.write_text(contenido, encoding="utf-8")


def listar_pendientes(evo_dir: Path) -> list[Flashcard]:
    """Todas las flashcards activas cuyo proximo_repaso <= hoy.
    Orden Anki: nivel más bajo primero. Excluye áreas pausadas (config)."""
    from config import settings
    if not evo_dir.exists():
        return []
    hoy = date.today()
    cards = []
    for md in evo_dir.rglob("*.md"):
        card = parse_flashcard(md)
        if (card and card.estado == "activo" and card.proximo_repaso <= hoy
                and settings.tema_esta_activo(card.area)):
            cards.append(card)
    # Orden Anki: N1 primero, luego N2, etc. Desempate por fecha de repaso.
    cards.sort(key=lambda c: (c.nivel_actual, c.proximo_repaso))
    return cards
