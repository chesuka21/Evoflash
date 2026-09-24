"""Ingestor de temas desde Obsidian — lee tus .md y genera flashcards evolutivas.
Analiza los temas de tus apuntes, detecta tu nivel por tema (aciertos/fallos),
y si tienes deficiencia, prioriza ese tema para repasar más."""
import re
import sys
import json
from pathlib import Path
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from config import settings

console = Console()

# Carpetas a ignorar en el vault (no son contenido estudio)
IGNORAR = {".obsidian", ".git", "Templates", "templates", "assets",
           "Resources", "resources", ".trash", "Excalidraw"}


def listar_temas(ruta: Path) -> list[dict]:
    """Lista los .md del vault como unidades de estudio."""
    if not ruta.exists():
        return []
    temas = []
    for md in ruta.rglob("*.md"):
        # Ignorar carpetas protegidas
        if any(part in md.parts for part in IGNORAR):
            continue
        # Solo notas con contenido (>50 chars)
        try:
            contenido = md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        if len(contenido) < 50:
            continue

        tema = detectar_tema(md, contenido)

        temas.append({
            "archivo": md.name,
            "ruta": str(md.name),
            "ruta_completa": str(md),
            "tema": tema,
            "concepto": md.stem,
            "palabras": len(contenido.split()),
            "modificado": datetime.fromtimestamp(md.stat().st_mtime).strftime("%Y-%m-%d"),
            "prioridad": 0,  # 0 = normal, 1 = déficit (repasar antes)
        })
    return temas


def detectar_tema(path: Path, contenido: str) -> str:
    """Detecta el 'tema' principal de una nota por heurísticas."""
    # 1. Carpeta contenedora
    carpeta = path.parent.name.lower()
    if carpeta in ("networking", "redes", "network", "networking"):
        return "Networking"
    if carpeta in ("security", "seguridad", "cybersecurity", "hacking"):
        return "Security"
    if carpeta in ("programacion", "programming", "python", "code"):
        return "Programming"
    # 2. Contenido: keywords frecuentes
    contenido_lower = contenido.lower()
    puntuaciones = {
        "Networking": sum(k in contenido_lower for k in ["ip", "dns", "router", "tcp", "udp", "http", "osi"]),
        "Security": sum(k in contenido_lower for k in ["firewall", "hash", "encrypt", "breach", "vulnerability", "privilege"]),
        "Programming": sum(k in contenido_lower for k in ["python", "javascript", "code", "function", "class", "def"]),
        "Linux": sum(k in contenido_lower for k in ["linux", "bash", "shell", "grep", "chmod", "sudo"]),
        "Databases": sum(k in contenido_lower for k in ["sql", "database", "select", "insert", "query"]),
    }
    if puntuaciones and max(puntuaciones.values()) > 0:
        return max(puntuaciones.keys(), key=lambda x: puntuaciones[x])
    return "General"


def generar_flashcards_desde_nota(ruta: Path, tema: str) -> list[dict]:
    """Extrae posibles preguntas de una nota usando patrones markdown."""
    try:
        contenido = ruta.read_text(encoding="utf-8")
    except Exception:
        return []

    # ⚠️ Skip notas que son casi solo imágenes/embeds (Resources etc.)
    texto_limpio = re.sub(r"!\[.*?\]\(.*?\)|\[\[.*?\]\]", "", contenido)
    if len(texto_limpio.strip()) < 80:
        return []

    # Patrones → preguntas candidatas
    preguntas = []

    # Títulos (# ## ###) como posibles conceptos
    titulos = re.findall(r"^#{1,3}\s+(.+?)(?:\n|$)", contenido, re.MULTILINE)
    for t in titulos[:3]:  # máx 3 títulos por nota
        preguntas.append({
            "concepto": t.strip(),
            "pregunta": f"¿Qué es {t.strip()}?",
            "respuesta_esperada": "Definición a extraer del contenido",
            "tipo": "teoría",
        })

    # Extracción de definiciones (texto después de ":")
    bloques = re.findall(r"\*\*(.+?)\*\*:\s*(.+?)(?=\n\n|\Z)", contenido, re.DOTALL)
    for titulo, cuerpo in bloques[:3]:
        preguntas.append({
            "concepto": titulo.strip(),
            "pregunta": f"Define {titulo.strip()}",
            "respuesta_esperada": cuerpo.strip()[:200],
            "tipo": "teoría",
        })

    # Enlaces [[Nota B]]
    enlaces = re.findall(r"\[\[(.+?)\]\]", contenido)
    if enlaces:
        preguntas.append({
            "concepto": enlaces[0],
            "pregunta": f"¿Cómo se relaciona {enlaces[0]} con este tema?",
            "respuesta_esperada": "Análisis del enlace interno",
            "tipo": "teoría",
        })

    return preguntas[:3]  # máx 3 por nota para no saturar


def sembrar_en_vault(preguntas: list[dict], carpeta_base: Path) -> int:
    """Escribe las preguntas generadas en el vault como flashcards."""
    if not preguntas:
        return 0

    # Limpiar: solo aceptar preguntas con concepto válido
    validas = [p for p in preguntas if len(p.get("concepto", "")) > 2]

    escritas = 0
    for i, p in enumerate(validas):
        cid = re.sub(r"[^a-z0-9_]", "", p["concepto"].lower().replace(" ", "_")[:30])
        if not cid:
            continue
        path = carpeta_base / f"{cid}.md"
        if path.exists():
            continue

        nivel = 1 if p.get("tipo") == "teoría" else 2
        contenido = f"""---
id: {cid}
tema: {p.get('tema', 'General')}
concepto: {p['concepto']}
nivel_actual: {nivel}
estado: activo
proximo_repaso: {date.today().isoformat()}
historial_aciertos: 0
---

# Q: {p['pregunta']}
**A:** {p['respuesta_esperada']}
"""
        path.write_text(contenido, encoding="utf-8")
        escritas += 1

    return escritas


def main_injest(temas_solo=False):
    """Flujo principal: leer todos los temas y generar flashcards."""
    vault = settings.vault_path()
    questions = settings.vault_flashcards_dir()

    console.print(f"[bold cyan]📂 Analizando tus apuntes en:[/bold cyan] {vault}")

    temas = listar_temas(vault)
    if not temas:
        console.print("[red]❌ No encontré notas en el vault[/bold red]")
        return

    # Agrupar por tema
    agrupados = {}
    for t in temas:
        agrupados.setdefault(t["tema"], []).append(t)

    # Mostrar resumen por tema
    tabla = Table(title=f"🗂️ Temas detectados en Obsidian ({len(temas)} notas)", box=box.ROUNDED)
    tabla.add_column("Tema", style="bold cyan", width=15)
    tabla.add_column("Notas", justify="center", width=8)
    tabla.add_column("Palabras", justify="center", width=10)
    tabla.add_column("Modificado", justify="center", width=12)

    for tema, notas in sorted(agrupados.items()):
        palabras = sum(n["palabras"] for n in notas)
        modificado = max(n["modificado"] for n in notas)
        tabla.add_row(tema, str(len(notas)), f"{palabras:,}", modificado)

    console.print(tabla)
    console.print()

    if temas_solo:
        console.print("[dim]👀 Solo mostré los temas. Usa --generar para crear flashcards.")
        return

    # Generar flashcards por cada nota importante
    console.print("[bold green]🛠️ Generando flashcards desde tus notas...[/bold green]")

    cards_totales = []
    for tema, notas in agrupados.items():
        for nota in notas[:5]:  # máx 5 notas por tema
            preguntas = generar_flashcards_desde_nota(Path(nota["ruta_completa"]), tema)
            cards_totales.extend(preguntas)
            # Añadir tema a cada preg
            for p in preguntas:
                p["tema"] = tema

    # Deduplicar
    vistos = set()
    unicas = []
    for p in cards_totales:
        key = p["pregunta"]
        if key not in vistos:
            vistos.add(key)
            unicas.append(p)

    console.print(f"[green]📝 {len(unicas)} preguntas únicas preparadas[/green]")

    # Sembrar en Questions vault
    escritas = sembrar_en_vault(unicas, questions)
    console.print(f"[bold green]✅ Sembradas en {questions}: {escritas} tarjetas[/bold green]")

    console.print(Panel.fit(
        f"[bold yellow]🎮 Listo! Ya tienes {escritas} tarjetas para jugar.[/bold yellow]\n"
        f"[dim]Revisa Questions/ en Obsidian y empieza a jugar[/dim]",
        border_style="yellow", box=box.DOUBLE,
    ))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Ingestor de temas desde Obsidian")
    ap.add_argument("--solo-temas", action="store_true", help="Solo listar temas, no sembrar")
    args = ap.parse_args()
    main_injest(temas_solo=args.solo_temas)
