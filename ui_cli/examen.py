"""EvoFlash — Modo Examen. N1→N4 evaluación progresiva sin trampas."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from config import settings
from vault_manager.vault_io import listar_pendientes, escribir_evolucion
from llm_interface.judge import LLMJudge

console = Console()


def preguntas_examen(area: str, max_nivel: int = 4) -> list:
    """Genera preguntas del área filtrada N1→N4."""
    todas = listar_pendientes(settings.questions_dir())
    return [c for c in todas if c.area == area and c.nivel_actual <= max_nivel]


def examinar(preguntas, judge: LLMJudge, xp_total: int = 0) -> int:
    for nivel in range(1, 5):
        nivel_cards = [c for c in preguntas if c.nivel_actual == nivel]
        if not nivel_cards:
            continue

        console.print(Panel(
            f"[bold yellow]📋 Nivel {nivel} — {len(nivel_cards)} tarjetas[/bold yellow]",
            border_style="yellow"
        ))

        for card in nivel_cards:
            console.rule(f"[bold]{card.concepto}[/bold] — Nivel {nivel} [{card.tema}]")
            console.print(Panel(f"[bold cyan]{card.pregunta}[/bold cyan]",
                                title="❓ Pregunta", border_style="cyan"))
            console.print("[yellow]💭 Tu respuesta:[/yellow]")
            respuesta = console.input("[yellow]>>> [/yellow]").strip()
            if not respuesta:
                continue

            with console.status("[bold cyan]🤖 Evaluando...", spinner="dots"):
                resultado = judge.evaluar_y_evolucionar(
                    tema=card.tema, concepto=card.concepto, nivel=card.nivel_actual,
                    pregunta=card.pregunta, respuesta_esperada=card.respuesta,
                    respuesta_usuario=respuesta,
                )

            ev = resultado.evaluacion
            if ev.es_correcta:
                XP = {1: 10, 2: 25, 3: 50, 4: 100}.get(card.nivel_actual, 10)
                xp_total += XP
                console.print(Panel(
                    f"[bold green]✅ CORRECTO +{XP} XP[/bold green]\n\n{ev.feedback_corto}",
                    border_style="green"
                ))
                if resultado.evolucion:
                    escribir_evolucion(card, resultado.evolucion.nueva_pregunta,
                                       resultado.evolucion.nueva_respuesta_esperada,
                                       resultado.evolucion.nuevo_nivel, ev.feedback_corto)
                    console.print(f"[magenta]🔥 ¡EVOLUCIÓN! Nivel {resultado.evolucion.nuevo_nivel}[/magenta]")
            else:
                console.print(Panel(
                    f"[bold red]❌ Incorrecto[/bold red]\n{ev.feedback_corto}\n"
                    f"[dim]Esperado: {card.respuesta}[/dim]",
                    border_style="red"
                ))

    return xp_total


def main_examen():
    console.print(Panel.fit(
        "[bold cyan]🔥 MODO EXAMEN EVOFLASH[/bold cyan]\n"
        "[dim]Evaluación N1 → N4, progresiva, sin opción a repasar el mismo tema[/dim]",
        border_style="cyan", box=box.DOUBLE
    ))

    preguntas = list(listar_pendientes(settings.questions_dir()))
    if not preguntas:
        console.print("[yellow]📭 No hay tarjetas pendientes.[/yellow]")
        return

    areas = sorted({c.area for c in preguntas if c.area})
    console.print("[bold]📚 Áreas disponibles para examen:[/bold]")
    for i, a in enumerate(areas, 1):
        n = sum(1 for c in preguntas if c.area == a)
        console.print(f"  {i}. {a} ({n} tarjetas)")

    ele = Prompt.ask("[blue]¿Qué área examen? (número o 'todas')[/blue]", default="todas")
    if ele.lower() == "todas":
        exam_preguntas = preguntas
    else:
        try:
            area_elegida = areas[int(ele) - 1]
            exam_preguntas = [c for c in preguntas if c.area == area_elegida]
            console.print(f"[green]🎯 Área: {area_elegida}[/green]")
        except (ValueError, IndexError):
            exam_preguntas = preguntas

    console.print(f"\n[bold green]📋 Tienes {len(exam_preguntas)} tarjetas. ¡Suerte![/bold green]")
    judge = LLMJudge()
    xp_total = examinar(exam_preguntas, judge)

    console.print(Panel.fit(
        f"[bold yellow]🏆 EXAMEN TERMINADO — {xp_total} XP ganados[/bold yellow]",
        border_style="yellow", box=box.DOUBLE
    ))


if __name__ == "__main__":
    main_examen()
