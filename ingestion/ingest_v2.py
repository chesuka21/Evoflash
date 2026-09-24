"""Ingestor v2 — el LLM lee tus apuntes y genera flashcards REALES.
Sin heurísticas tontas: cada nota se manda a Gemini y le pide preguntas precisas."""
import re
import sys
import json
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich import box

from config import settings

console = Console()

IGNORAR = {".obsidian", ".git", "templates", "assets", "resources",
           ".trash", "excalidraw", "questions", "evoflash", "venv"}
MIN_TEXTO_UTIL = 150  # ignorar notas con menos texto real que esto


def es_nota_valida(md: Path) -> str | None:
    """Devuelve el contenido si la nota sirve para estudio, None si no."""
    if any(p.lower() in IGNORAR for p in md.parts):
        return None
    try:
        contenido = md.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return None
    # Medir texto real, sin imágenes/embeds/links
    limpio = re.sub(r"!\[.*?\]\(.*?\)", "", contenido)
    limpio = re.sub(r"!?\[\[[^\]]*\]\]", "", limpio)
    if len(limpio.strip()) < MIN_TEXTO_UTIL:
        return None
    return contenido[:6000]  # cap para no quemar tokens


def detectar_tema(path: Path) -> str:
    carpeta = path.parent.name.lower()
    mapa = {
        "networking": "Networking", "redes": "Networking", "network": "Networking",
        "security": "Security", "seguridad": "Security", "cybersecurity": "Security",
        "hacking": "Security", "linux": "Linux", "bash": "Linux", "shell": "Linux",
        "python": "Programming", "programacion": "Programming",
        "bases": "Databases", "sql": "Databases", "database": "Databases",
    }
    for k, v in mapa.items():
        if k in carpeta:
            return v
    return "General"


PROMPT_NOTA = """Eres un generador de flashcards educativas. Lee este apunte del estudiante y genera entre 2 y 4 flashcards de Nivel 1 (teoría) basadas ÚNICAMENTE en el contenido real del apunte.

REGLAS ESTRICTAS:
1. Cada pregunta debe poder responderse CON el contenido del apunte. No inventes nada.
2. PROHIBIDAS preguntas meta ("¿Cómo se relaciona X...?", "¿De qué trata este tema?") — preguntas concretas de contenido.
3. PROHIBIDO mencionar "el apunte", "el texto", "según el documento" — la pregunta debe ser auto-contenida (ej. NO "¿Cuáles son los niveles mencionados en el apunte?" SÍ "¿Cuáles son los niveles de clasificación de activos de información?").
4. Si el apunte tiene definiciones, haz preguntas de definición. Si tiene pasos/comandos, pregunta el paso/comando exacto.
5. El 'tema' debe ser EXACTAMENTE: {tema_real} (la carpeta de origen, no lo inventes).
6. concepto: subtema específico (corto, 2-4 palabras).

Título del apunte: {titulo}
Carpeta de origen del apunte: {tema_real}
Contenido del apunte:
\"\"\"
{contenido}
\"\"\"

Responde ÚNICAMENTE con JSON válido:
[{{"tema": "{tema_real}", "concepto": "...", "pregunta": "...", "respuesta_esperada": "..."}}]
"""


def generar_cards_desde_nota(client, model: str, nota: Path, contenido: str) -> list[dict]:
    tema_real = detectar_tema(nota)
    prompt = PROMPT_NOTA.format(titulo=nota.stem, contenido=contenido, tema_real=tema_real)
    try:
        r = client.models.generate_content(
            model=model, contents=prompt,
            config={"response_mime_type": "application/json",
                    "temperature": 0.3, "max_output_tokens": 3000},
        )
        raw = "".join(p.text for p in r.candidates[0].content.parts if getattr(p, "text", None))
        cards = json.loads(raw)
        return cards if isinstance(cards, list) else []
    except Exception as e:
        console.print(f"   [red]⚠️ Error en {nota.name}: {type(e).__name__}[/red]")
        return []


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", s.lower().replace(" ", "_"))[:40]


def main():
    vault = settings.vault_path()
    questions = settings.questions_dir()
    questions.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold cyan]📂 Analizando apuntes en:[/bold cyan] {vault}")

    from llm_interface.judge import LLMJudge
    judge = LLMJudge()
    if judge.mock:
        console.print("[red]❌ Sin API key — el ingester v2 necesita Gemini.[/red]")
        return

    # Recolectar notas válidas
    notas = []
    for md in vault.rglob("*.md"):
        contenido = es_nota_valida(md)
        if contenido:
            notas.append((md, contenido))

    console.print(f"[green]📝 {len(notas)} notas útiles encontradas[/green] "
                  f"[dim](~{len(notas)} llamadas a Gemini, ~3s cada una)[/dim]\n")

    total, saltadas = 0, 0
    for md, contenido in notas:
        console.print(f"[dim]📖 {md.name}[/dim]")
        cards = generar_cards_desde_nota(judge.client, settings.LLM_MODEL, md, contenido)
        tema_nota = detectar_tema(md)
        for c in cards:
            cid = slug(c.get("concepto", "")) or slug(md.stem)
            if not cid:
                continue
            path = questions / f"{cid}.md"
            if path.exists():
                saltadas += 1
                continue
            rel = md.relative_to(vault).as_posix()
            path.write_text(f"""---
id: {cid}
tema: {tema_nota}
concepto: {c.get("concepto", md.stem)}
nivel_actual: 1
estado: activo
proximo_repaso: {date.today().isoformat()}
historial_aciertos: 0
fuente: "{rel}"
---

# Q: {c.get("pregunta", "")}
**A:** {c.get("respuesta_esperada", "")}
""", encoding="utf-8")
            total += 1
            console.print(f"   [green]🌱 {c.get('concepto', '')}[/green]")

    console.print(Panel.fit(
        f"[bold yellow]🎮 Ingesta completa[/bold yellow]\n"
        f"✅ Nuevas: {total} | ⏭️ Ya existían: {saltadas}\n"
        f"[dim]Juega con: evoflash.bat[/dim]",
        border_style="yellow", box=box.DOUBLE,
    ))


if __name__ == "__main__":
    main()
