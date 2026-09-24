"""EvoFlash — Gestor de Exámenes. Tu decides cuándo y de qué temas."""
import sys
import json
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from config import settings
from vault_manager.vault_io import listar_pendientes

console = Console()
EXAMINES_FILE = settings.ROOT / "config" / "examenes.json"


def cargar_examenes():
    if not EXAMINES_FILE.exists():
        return {"examenes": []}
    return json.loads(EXAMINES_FILE.read_text(encoding="utf-8"))


def guardar_examenes(data):
    EXAMINES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print("[green]✅ Config guardada[/green]")


def mostrar_examenes(data):
    console.print(Panel.fit(
        "[bold magenta]📅 CONFIGURADOR DE EXÁMENES[/bold magenta]\n"
        "[dim]Define cuándo examinarte y de qué temas[/dim]",
        border_style="magenta", box=box.DOUBLE
    ))

    if not data["examenes"]:
        console.print("[yellow]No hay exámenes programados.[/yellow]")
        return

    # Ordenar por fecha
    examenes = sorted(data["examenes"], key=lambda x: x["fecha"])

    table = Table(box=box.ROUNDED, title="Tus exámenes")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Examen", style="green")
    table.add_column("Fecha", style="yellow")
    table.add_column("Días", justify="right")
    table.add_column("Áreas", style="blue")
    table.add_column("Notas", style="dim")

    hoy = date.today()
    for i, ex in enumerate(examenes, 1):
        f = date.fromisoformat(ex["fecha"])
        dias = (f - hoy).days
        estado = "🔴 YA PASÓ" if dias < 0 else "🟡 URGENTE" if dias <= 7 else "🟢"
        table.add_row(
            str(i), ex["nombre"], ex["fecha"],
            f"{dias}d" if dias >= 0 else "—",
            ", ".join(ex["areas"]),
            ex.get("notas", "")[:30]
        )

    console.print(table)


def menu_principal():
    while True:
        data = cargar_examenes()
        mostrar_examenes(data)

        console.print("""
[bold]¿Qué hacer?[/bold]
  1. ➕ Programar nuevo examen
  2. 🗑️  Eliminar examen
  3. ▶️  Tomar examen AHORA (modo intensivo)
  4. 📋 Ver cuántas tarjetas tocan por área
  5. 📅 Ver calendario por semana
  0. 🔙 Salir
""")
        op = Prompt.ask("[blue]Elige[/blue]", default="0")

        if op == "1":
            nombre = Prompt.ask("Nombre del examen")
            fecha = Prompt.ask("Fecha (YYYY-MM-DD)", default=str(date.today()))
            areas = Prompt.ask("Áreas separadas por coma (ej: Cursos/Google cybersecurity,Networking)").split(",")
            areas = [a.strip() for a in areas if a.strip()]
            dificultad = Prompt.ask("Nivel máximo (1-4)", default="4")
            notas = Prompt.ask("Notas extras", default="")

            data["examenes"].append({
                "nombre": nombre,
                "fecha": fecha,
                "areas": areas,
                "dificultad": f"N1—N{dificultad}",
                "notas": notas,
            })
            guardar_examenes(data)

        elif op == "2":
            if not data["examenes"]:
                console.print("[yellow]No hay exámenes para eliminar.[/yellow]")
                continue
            idx = Prompt.ask("Elige el número a eliminar")
            try:
                i = int(idx) - 1
                borrado = data["examenes"].pop(i)
                console.print(f"[red]❌ Eliminado: {borrado['nombre']}[/red]")
                guardar_examenes(data)
            except (ValueError, IndexError):
                console.print("[red]Número inválido.[/red]")

        elif op == "3":
            if not data["examenes"]:
                console.print("[yellow]No hay exámenes. Primero programa uno.[/yellow]")
                continue
            console.print("[bold]Elige examen:[/bold]")
            for i, ex in enumerate(data["examenes"], 1):
                console.print(f"  {i}. {ex['nombre']} ({ex['fecha']})")
            idx = Prompt.ask("Número")
            try:
                i = int(idx) - 1
                ejecutar_examen(data["examenes"][i])
            except (ValueError, IndexError):
                console.print("[red]Número inválido.[/red]")

        elif op == "4":
            todas = listar_pendientes(settings.questions_dir())
            por_area = {}
            for c in todas:
                por_area.setdefault(c.area, 0)
                por_area[c.area] += 1
            console.print("\n[bold]📊 Tarjetas pendientes por área:[/bold]")
            for area, n in sorted(por_area.items(), key=lambda x: -x[1]):
                console.print(f"  {area}: {n} tarjetas")

        elif op == "5":
            hoy = date.today()
            dias = Prompt.ask("¿Cuántos días hacia adelante?", default="7")
            dias = int(dias)
            data2 = cargar_examenes()
            proximos = [ex for ex in data2["examenes"]
                        if hoy <= date.fromisoformat(ex["fecha"]) <= hoy.fromordinal(hoy.toordinal() + dias)]
            console.print(f"[bold]📅 Próximos {dias} días:[/bold]")
            for ex in sorted(proximos, key=lambda x: x["fecha"]):
                f = date.fromisoformat(ex["fecha"])
                days = (f - hoy).days
                console.print(f"  {f} ({days}d): {ex['nombre']} — {', '.join(ex['areas'])}")

        elif op == "0":
            break


def ejecutar_examen(examen):
    """Ejecuta un examen específico por áreas, con nivel máximo."""
    todas = listar_pendientes(settings.questions_dir())
    max_nivel = int(examen.get("dificultad", "N1—N4").split("—N")[1])

    exam_preguntas = [c for c in todas
                      if c.area in examen["areas"]
                      and c.nivel_actual <= max_nivel]

    if not exam_preguntas:
        console.print("[yellow]📭 No hay tarjetas pendientes para estas áreas.[/yellow]")
        return

    console.print(Panel.fit(
        f"[bold cyan]🔥 EXAMEN: {examen['nombre']}[/bold cyan]\n"
        f"[dim]{len(exam_preguntas)} tarjetas | Temas: {', '.join(examen['areas'])} | Nivel: N1→N{max_nivel}[/dim]\n"
        f"[yellow]¡No puedes saltar tarjetas! Evaluación rigurosa.[/yellow]",
        border_style="cyan", box=box.DOUBLE
    ))

    judge = LLMJudge()
    xp_total = 0
    aciertos = 0
    fallos = 0

    # Progresión por nivel
    for nivel in range(1, max_nivel + 1):
        nivel_cards = [c for c in exam_preguntas if c.nivel_actual == nivel]
        if not nivel_cards:
            continue

        console.print(Panel(
            f"[bold yellow]📋 NIVEL {nivel} — {len(nivel_cards)} tarjetas[/bold yellow]",
            border_style="yellow"
        ))

        for card in nivel_cards:
            console.rule(f"[bold]{card.concepto}[/bold] — Nivel {nivel} [{card.tema}]")
            console.print(Panel(f"[bold cyan]{card.pregunta}[/bold cyan]",
                                title="❓ Pregunta", border_style="cyan"))
            console.print("[yellow]💭 Tu respuesta:[/yellow]")
            respuesta = console.input("[yellow]>>> [/yellow]").strip()
            if not respuesta:
                console.print("[dim]⏭️ Saltada[/dim]")
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
                aciertos += 1
                console.print(Panel(
                    f"[bold green]✅ CORRECTO +{XP} XP[/bold green]\n\n{ev.feedback_corto}",
                    border_style="green"
                ))
                if resultado.evolucion:
                    from vault_manager.vault_io import escribir_evolucion
                    escribir_evolucion(card, resultado.evolucion.nueva_pregunta,
                                       resultado.evolucion.nueva_respuesta_esperada,
                                       resultado.evolucion.nuevo_nivel, ev.feedback_corto)
                    console.print(f"[magenta]🔥 ¡EVOLUCIÓN! Nivel {resultado.evolucion.nuevo_nivel}[/magenta]")
            else:
                fallos += 1
                console.print(Panel(
                    f"[bold red]❌ Incorrecto[/bold red]\n{ev.feedback_corto}\n"
                    f"[dim]Esperado: {card.respuesta}[/dim]",
                    border_style="red"
                ))

    # Resumen final
    console.print(Panel.fit(
        f"[bold yellow]🏆 EXAMEN TERMINADO[/bold yellow]\n\n"
        f"Aciertos: [green]{aciertos}[/green] | Fallos: [red]{fallos}[/red] | Pendientes: [yellow]{len(exam_preguntas) - aciertos - fallos}[/yellow]\n"
        f"XP total: [cyan]{xp_total}[/cyan]\n"
        f"Fecha examen: {examen['fecha']} | Tu balance: {'✅ Pasas' if aciertos > fallos else '❌ Repasa primero'}",
        border_style="yellow", box=box.DOUBLE
    ))


if __name__ == "__main__":
    menu_principal()
