"""EvoFlash CLI — Terminal RPG UI con Rich
v0.3: Fix Progress-overlay bug, Boss Battles, Practice mode, imágenes"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

from config import settings
from vault_manager.vault_io import listar_pendientes, escribir_evolucion
from llm_interface.judge import LLMJudge

console = Console()
XP_POR_NIVEL = {1: 10, 2: 25, 3: 50, 4: 100}
XP_BASE_BOSS = 500
XP_PRACTICE = 30


def banner():
    console.print(Panel.fit(
        "[bold magenta]⚡ EVOFLASH ⚡[/bold magenta]\n"
        "[dim]Sistema de Aprendizaje Evolutivo v0.3[/dim]",
        border_style="magenta", box=box.DOUBLE,
    ))


def _plantar_sugerencias(card, sugerencias, seleccion=None):
    """Escribe solo las sugerencias elegidas por el usuario.

    Args:
        seleccion: lista de índices 1-based (ej. [1, 3]) o None = todas
    """
    from pathlib import Path as _P
    from datetime import date as _date
    base = _P(card.path).parent
    plantadas = 0
    for i, s in enumerate(sugerencias, 1):
        if seleccion and i not in seleccion:
            continue
        cid = s.concepto.lower().replace(" ", "_")[:40] + f"_{_date.today().strftime('%m%d')}"
        path = base / f"{cid}.md"
        if path.exists():
            continue
        path.write_text(f"""---
id: {cid}
tema: {card.tema}
concepto: {s.concepto}
nivel_actual: {s.nivel}
estado: activo
proximo_repaso: {_date.today().isoformat()}
historial_aciertos: 0
---

# Q: {s.pregunta}
**A:** {s.respuesta_esperada}
""", encoding="utf-8")
        plantadas += 1
        console.print(f"   [green]🌱 Plantada:[/green] {path.name}")
    if not plantadas:
        console.print("   [dim]Esos nodos ya existen en tu vault.[/dim]")


def _panel_practica(card):
    """Panel visual para preguntas prácticas"""
    tabla = Table(show_header=False, box=box.ROUNDED, border_style="yellow", padding=(0, 2))
    tabla.add_column("Tipo", style="bold yellow", width=12)
    tabla.add_column("Instrucción", style="white")
    tabla.add_row("🖥️ Comando", f"Abre tu terminal y ejecuta: [bold cyan]{card.practice_cmd}[/bold cyan]")
    tabla.add_row("📋 Reporta", "¿Qué observaste en la salida?")
    tabla.add_row("🎯 Evalúa", "La IA comparará tu observación con la salida esperada")
    return Panel(tabla, title="🛠️ PRÁCTICA — MODO MANOS EN LA MASA", border_style="yellow")


def _panel_escenario(card):
    """Panel para roleplay — Boss Battle (Nivel 4)"""
    return Panel(
        f"[bold red]{card.concepto}[/bold red]\n\n{card.pregunta}",
        title="🚨 ⚔️ BOSS BATTLE — ESCENARIO DE TROUBLESHOOTING ⚔️",
        border_style="red",
        box=box.DOUBLE
    )


def _panel_con_imagen(card):
    """Panel para preguntas/respuestas con imagen"""
    partes = [f"[bold cyan]{card.pregunta}[/bold cyan]"]
    if card.imagen_pregunta:
        partes.append(f"\n[dim]🖼️ Imagen: {card.imagen_pregunta}[/dim]")
        partes.append("[dim](Ábrela en Obsidian para verla)[/dim]")
    return Panel(
        "\n".join(partes),
        title="❓ Pregunta (con imagen)",
        border_style="cyan"
    )


def _resolver_practica_con_llm(judge: LLMJudge, card, observacion_usuario: str):
    """Evalúa la observación del usuario en modo práctica."""
    prompt_extra = f"""
PRÁCTICA TÉCNICA — MODO PRACTICE

Comando dado: {card.practice_cmd}
Salida esperada (resumen): {card.practice_esperada}
Observación del usuario: "{observacion_usuario}"

1. Evalúa si la observación coincide con lo que DEBERÍA salir
2. Si es correcta, genera la siguiente práctica (escalonamiento de dificultad):
   - Nivel 2: mismo comando, caso más complejo
   - Nivel 3: troubleshooting relacionado
   - Nivel 4: escenario arquitectónico que use este comando

JSON válido:
{{
  "evaluacion": {{"es_correcta": true|false, "feedback_corto": "..."}},
  "evolucion": {{"nuevo_nivel": {min(card.nivel_actual + 1, 4)},
                 "nueva_pregunta": "práctica siguiente",
                 "nueva_respuesta_esperada": "salida esperada"}},
  "sugerencias": []
}}
"""
    return judge.evaluar_y_evolucionar(
        tema=card.tema, concepto=card.concepto, nivel=card.nivel_actual,
        pregunta=card.pregunta, respuesta_esperada=card.practice_esperada,
        respuesta_usuario=observacion_usuario,
    )


def jugar_sesion(mock: bool = False):
    banner()
    vault_dir = settings.vault_flashcards_dir()
    console.print(f"[dim]📂 Vault: {vault_dir}[/dim]")
    console.print(
        f"[dim]🤖 LLM: {'MOCK (dev)' if mock or not settings.has_api_key() else settings.LLM_MODEL}[/dim]\n"
    )

    pendientes = listar_pendientes(vault_dir)
    if not pendientes:
        console.print("[yellow]📭 No hay tarjetas pendientes de repaso hoy.[/yellow]")
        return

    judge = LLMJudge(force_mock=mock)
    xp_total = 0

    # ── FILTRO POR ÁREA (carpeta real del apunte) ──────────────
    areas_disponibles = sorted({c.area for c in pendientes if c.area})
    if len(areas_disponibles) > 1:
        console.print("[bold cyan]📚 Selecciona el área a repasar hoy:[/bold cyan]")
        for i, t in enumerate(areas_disponibles, 1):
            n = sum(1 for c in pendientes if c.area == t)
            console.print(f"  {i}. {t} ({n} tarjetas)")
        console.print(f"  0. Todas las áreas ({len(pendientes)} tarjetas)")
        ele = Prompt.ask("[blue]Elige un número", default="0").strip()
        try:
            idx = int(ele)
            if idx == 0:
                pass  # todas
            elif 1 <= idx <= len(areas_disponibles):
                elegida = areas_disponibles[idx - 1]
                pendientes = [c for c in pendientes if c.area == elegida]
                console.print(f"[green]🎯 Filtrado: {elegida}[/green]")
            else:
                console.print("[dim]Opción no válida — usando todas[/dim]")
        except ValueError:
            console.print("[dim]Opción no válida — usando todas[/dim]")
        console.print()

    # ── Mostrar tabla de pendientes ────────────────────────────
    tabla = Table(title="📋 Flashcards Pendientes (Nivel bajo primero)", box=box.ROUNDED)
    tabla.add_column("#", style="cyan", width=4)
    tabla.add_column("Concepto", style="bold")
    tabla.add_column("Área", style="dim", width=22)
    tabla.add_column("Nivel", justify="center")
    tabla.add_column("Tipo", style="dim")
    for i, c in enumerate(pendientes, 1):
        if c.es_boss_battle:
            tipo = "🚨 BOSS"
        elif c.practice_cmd:
            tipo = "🛠️ Práctica"
        else:
            tipo = "🧠 Teoría"
        tabla.add_row(str(i), c.concepto, c.area, f"N{c.nivel_actual}", tipo)
    console.print(tabla)
    console.print()

    # ── BUCLE PRINCIPAL (sin Progress para evitar overlay) ─────
    for idx, card in enumerate(pendientes, 1):
        console.rule(
            f"[bold]{card.concepto}[/bold] — Nivel {card.nivel_actual} [{card.tema}]"
            f"  [dim]({idx}/{len(pendientes)})[/dim]"
        )

        # ── ELEGIR PANEL SEGÚN TIPO ────────────────────────────
        if card.es_boss_battle:
            console.print(_panel_escenario(card))
            console.print("[bold red]⚠️  Tienes libertad: responde paso a paso. La IA evaluará tu lógica completa.[/bold red]\n")
        elif card.practice_cmd:
            console.print(_panel_practica(card))
        else:
            console.print(_panel_con_imagen(card))

        # ── CAPTURAR RESPUESTA (con spinner) ───────────────────
        console.print("[bold yellow]💭 Tu respuesta:[/bold yellow]")
        respuesta = console.input("[yellow]>>> [/yellow]").strip()
        if not respuesta:
            console.print("[dim]Saltada...[/dim]\n")
            continue

        # ── EVALUAR CON SPINNER VISIBLE ────────────────────────
        try:
            with console.status("[bold cyan]🤖 Evaluando con IA...", spinner="dots"):
                if card.practice_cmd:
                    resultado = _resolver_practica_con_llm(judge, card, respuesta)
                else:
                    resultado = judge.evaluar_y_evolucionar(
                        tema=card.tema, concepto=card.concepto, nivel=card.nivel_actual,
                        pregunta=card.pregunta, respuesta_esperada=card.respuesta,
                        respuesta_usuario=respuesta,
                    )
                if card.es_boss_battle:
                    resultado.evolucion = None  # Boss no evoluciona, solo XP
        except RuntimeError as e:
            console.print(f"[red]❌ Error de la IA:[/red] {e}")
            console.print("[yellow]⏱️  Gemini está saturado o sin conexión. Pasa a la siguiente tarjeta o espera unos minutos.[/yellow]\n")
            continue  # no detengan la sesión completa por un solo fallo

        # ── MOSTRAR RESULTADO ──────────────────────────────────
        ev = resultado.evaluacion
        if ev.es_correcta:
            card.marcar_acierto()
            xp = XP_POR_NIVEL.get(card.nivel_actual, 10)
            if card.es_boss_battle:
                xp = XP_BASE_BOSS
            elif card.practice_cmd:
                xp = XP_PRACTICE
            xp_total += xp

            console.print(Panel(
                f"[bold green]✅ CORRECTO +{xp} XP[/bold green]\n\n{ev.feedback_corto}",
                border_style="green"
            ))

            if resultado.evolucion and not card.es_boss_battle:
                escribir_evolucion(
                    card, resultado.evolucion.nueva_pregunta,
                    resultado.evolucion.nueva_respuesta_esperada,
                    resultado.evolucion.nuevo_nivel, ev.feedback_corto,
                )
                console.print(
                    f"[magenta]🔥 ¡EVOLUCIÓN! '{card.concepto}' "
                    f"subió a Nivel {resultado.evolucion.nuevo_nivel}[/magenta]"
                )
            elif card.es_boss_battle:
                # Boss Battle: persistir acierto para que NO reaparezca mañana
                escribir_evolucion(
                    card, card.pregunta, card.respuesta,
                    card.nivel_actual, ev.feedback_corto,
                )
                console.print("[bold gold1]👑 ¡BOSS DERROTADO! +500 XP — dominaste el Nivel 4[/bold gold1]")
        else:
            card.marcar_fallo()
            escribir_evolucion(
                card, card.pregunta, card.respuesta,
                card.nivel_actual, ev.feedback_corto,
            )
            console.print(Panel(
                f"[bold red]❌ Incorrecto[/bold red]\n"
                f"{ev.feedback_corto}\n"
                f"[dim]Esperado: {card.respuesta}[/dim]",
                border_style="red"
            ))

        # ── SUGERENCIAS (solo si acertaste, no al fallar) ──────
        if resultado.sugerencias and ev.es_correcta:
            console.print(
                "\n[bold blue]💡 Sugerencias del grafo — nuevos nodos relacionados:[/bold blue]"
            )
            for i, s in enumerate(resultado.sugerencias, 1):
                console.print(
                    f"  [cyan]{i}.[/cyan] [bold]{s.concepto}[/bold] (N{s.nivel}): {s.pregunta}"
                )
            plantar = Prompt.ask(
                "[blue]¿Plantar alguna? (ej: 2 o 1,3) [Enter=saltar]",
                default="", show_default=False,
            ).strip()
            if plantar:
                try:
                    indices = [int(x.strip()) for x in plantar.split(",") if x.strip()]
                    _plantar_sugerencias(card, resultado.sugerencias, seleccion=indices)
                except ValueError:
                    console.print("[red]Formato inválido — usa números separados por coma[/red]")

        console.print()  # espacio entre tarjetas

    # ── RESUMEN FINAL ─────────────────────────────────────────────
    console.print(Panel.fit(
        f"[bold yellow]🏆 SESIÓN COMPLETA — {xp_total} XP ganados[/bold yellow]\n"
        f"[dim]Revisa tu Vault → Obsidian para ver el progreso[/dim]",
        border_style="yellow", box=box.DOUBLE,
    ))


if __name__ == "__main__":
    mock_flag = "--mock" in sys.argv
    jugar_sesion(mock=mock_flag)
