"""Gestor de áreas de estudio — activa/pausa temas sin borrar nada del vault."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from config import settings

console = Console()


def listar_carpetas_vault(max_nivel: int = 2) -> list[str]:
    """Carpetas disponibles hasta max_nivel (ej: 'Cursos/Google cybersecurity')."""
    ignore = {".obsidian", ".git", "templates", "assets", "resources",
              ".trash", "excalidraw", "questions", "evoflash", "venv"}
    vault = settings.vault_path()
    if not vault.exists():
        return []

    rutas = []
    for p in vault.rglob("*"):
        if not p.is_dir():
            continue
        if any(part.lower() in ignore for part in p.parts):
            continue
        rel = p.relative_to(vault).as_posix()
        # Nivel 1-2 (ej. "Cursos" o "Cursos/Google cybersecurity")
        if rel.count("/") < max_nivel:
            rutas.append(rel)
    return sorted(set(rutas))


def main():
    console.print(Panel.fit(
        "[bold cyan]📚 Gestor de Áreas de Estudio[/bold cyan]\n"
        "[dim]Pausa temas que no estudias hoy, actívalos cuando quieras volver.[/dim]",
        border_style="cyan", box=box.DOUBLE))

    cfg = settings.cargar_temas()
    todas = listar_carpetas_vault()

    while True:
        console.print()
        tabla = Table(title="Estado actual", box=box.ROUNDED)
        tabla.add_column("#", style="cyan", width=4)
        tabla.add_column("Carpeta", style="bold")
        tabla.add_column("Estado", style="dim")
        for i, c in enumerate(todas, 1):
            if c.lower() in [p.lower() for p in cfg["pausados"]]:
                estado = "⏸️  Pausada"
            elif not cfg["activos"] or c.lower() in [a.lower() for a in cfg["activos"]]:
                estado = "✅ Activa"
            else:
                estado = "⏸️  No incluida"
            tabla.add_row(str(i), c, estado)
        console.print(tabla)
        console.print("[dim]⚙️  Si 'activos' está vacío, todas (menos pausadas) están activas.[/dim]")

        op = Prompt.ask(
            "\n[bold]Acción[/bold] ([cyan]P[/cyan]=Pausar / [cyan]A[/cyan]=Activar / [cyan]R[/cyan]=Reset / Enter=Salir)",
            default="").strip().lower()

        if not op:
            break
        elif op == "r":
            cfg = {"activos": [], "pausados": []}
            console.print("[yellow]Reset: todas las carpetas activas.[/yellow]")
        elif op == "p":
            try:
                n = int(Prompt.ask("Número a pausar").strip())
                if 1 <= n <= len(todas):
                    carpeta = todas[n - 1]
                    if carpeta not in cfg["pausados"]:
                        cfg["pausados"].append(carpeta)
                    if carpeta in cfg["activos"]:
                        cfg["activos"].remove(carpeta)
                    console.print(f"[yellow]⏸️  Pausada: {carpeta}[/yellow]")
                else:
                    console.print("[red]Número inválido.[/red]")
            except ValueError:
                console.print("[red]Formato inválido.[/red]")
        elif op == "a":
            try:
                n = int(Prompt.ask("Número a activar").strip())
                if 1 <= n <= len(todas):
                    carpeta = todas[n - 1]
                    if carpeta in cfg["pausados"]:
                        cfg["pausados"].remove(carpeta)
                    if carpeta not in cfg["activos"]:
                        cfg["activos"].append(carpeta)
                    console.print(f"[green]✅ Activada: {carpeta}[/green]")
                else:
                    console.print("[red]Número inválido.[/red]")
            except ValueError:
                console.print("[red]Formato inválido.[/red]")

        settings.TEMAS_CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
        console.print(f"[green]✅ Guardado en {settings.TEMAS_CONFIG.name}[/green]")

    console.print("\n[bold green]Listo. Tus áreas así quedaron:[/bold green]")
    console.print(f"  Activas: {cfg['activos'] or 'TODAS (menos pausadas)'}")
    console.print(f"  Pausadas: {cfg['pausados'] or 'ninguna'}")


if __name__ == "__main__":
    main()
