"""Stats — resumen de tu progreso por tema (toca practicar lo más débil)."""
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config import settings
from vault_manager.vault_io import parse_flashcard


def recolectar() -> list:
    questions = settings.questions_dir()
    if not questions.exists():
        return []
    cards = []
    for md in questions.glob("*.md"):
        c = parse_flashcard(md)
        if c:
            cards.append(c)
    return cards


def main():
    console = Console()
    cards = recolectar()
    if not cards:
        console.print("[yellow]📭 No hay flashcards en tu vault todavía.[/yellow]")
        return

    # Stats por tema
    por_tema = defaultdict(lambda: {"total": 0, "aciertos": 0, "n1": 0, "n2": 0, "n3": 0, "n4": 0, "bosses": 0})
    for c in cards:
        t = c.tema or "General"
        s = por_tema[t]
        s["total"] += 1
        s["aciertos"] += c.historial_aciertos
        if c.nivel_actual == 4:
            s["bosses"] += 1
        else:
            s[f"n{c.nivel_actual}"] += 1

    # Tabla de progreso
    tabla = Table(title="📊 Tu Skill Tree — Progreso por Tema", box=box.ROUNDED)
    tabla.add_column("Tema", style="bold cyan")
    tabla.add_column("Tarjetas", justify="center")
    tabla.add_column("N1", justify="center", style="green")
    tabla.add_column("N2", justify="center", style="yellow")
    tabla.add_column("N3", justify="center", style="magenta")
    tabla.add_column("N4/Boss", justify="center", style="bold red")
    tabla.add_column("Aciertos", justify="center")
    tabla.add_column("Estado", style="dim")

    temas_ordenados = sorted(por_tema.items(), key=lambda x: x[1]["total"], reverse=True)
    for tema, s in temas_ordenados:
        # Heurística: si tiene muchas N1 y pocos aciertos, está débil
        if s["n1"] >= 3 and s["aciertos"] < s["n1"]:
            estado = "🔴 Repasar urgente"
        elif s["bosses"] > 0:
            estado = "🟢 Dominado"
        elif s["n2"] + s["n3"] > s["n1"]:
            estado = "🟡 En progreso"
        else:
            estado = "🔵 Empezando"
        tabla.add_row(tema, str(s["total"]), str(s["n1"]), str(s["n2"]),
                      str(s["n3"]), str(s["bosses"]), str(s["aciertos"]), estado)

    console.print(tabla)

    # Tema más débil
    debil = min(temas_ordenados, key=lambda x: x[1]["aciertos"]) if temas_ordenados else None
    if debil:
        console.print()
        console.print(Panel.fit(
            f"[bold red]🎯 Tema más débil: {debil[0]}[/bold red]\n"
            f"Aciertos acumulados: {debil[1]['aciertos']} | Deberías repasarlo hoy.",
            border_style="red"
        ))


if __name__ == "__main__":
    main()
