"""EvoFlash Web — juego completo (sin CLI)"""
import json
import sys
import traceback
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from vault_manager.vault_io import listar_pendientes, parse_flashcard, escribir_evolucion
from llm_interface.judge import LLMJudge

HERE = Path(__file__).parent
judge = None


def get_judge():
    global judge
    if judge is None:
        judge = LLMJudge()
    return judge


def card_to_json(c):
    return {
        "id": c.id, "concepto": c.concepto, "tema": c.tema, "area": c.area,
        "nivel": c.nivel_actual, "aciertos": c.historial_aciertos,
        "pregunta": c.pregunta, "es_boss": c.es_boss_battle,
        "es_practice": bool(c.practice_cmd), "practice_cmd": c.practice_cmd,
        "practice_esperada": c.practice_esperada,
        "path": c.path,
    }


def api_pending(area=None):
    todas = listar_pendientes(settings.questions_dir())
    areas = sorted({c.area for c in todas if c.area})
    cards = [c for c in todas if c.area == area] if area else todas
    return {"cards": [card_to_json(c) for c in cards], "areas": areas}


def api_answer(card_path, respuesta):
    card = parse_flashcard(Path(card_path))
    if not card:
        return {"ok": False, "error": "tarjeta no encontrada"}
    j = get_judge()
    resultado = j.evaluar_y_evolucionar(
        tema=card.tema, concepto=card.concepto, nivel=card.nivel_actual,
        pregunta=card.pregunta, respuesta_esperada=card.respuesta,
        respuesta_usuario=respuesta,
    )
    ev = resultado.evaluacion
    XP = {1: 10, 2: 25, 3: 50, 4: 100}

    out = {
        "ok": True,
        "correcta": ev.es_correcta,
        "feedback": ev.feedback_corto,
        "sugerencias": [s.model_dump() for s in resultado.sugerencias]
                       if ev.es_correcta else [],
    }
    if ev.es_correcta:
        card.marcar_acierto()
        xp = 500 if card.es_boss_battle else (30 if card.practice_cmd else XP.get(card.nivel_actual, 10))
        out["xp"] = xp
        if card.es_boss_battle:
            escribir_evolucion(card, card.pregunta, card.respuesta,
                               card.nivel_actual, ev.feedback_corto)
            out["boss_derrotado"] = True
        elif resultado.evolucion:
            escribir_evolucion(card, resultado.evolucion.nueva_pregunta,
                               resultado.evolucion.nueva_respuesta_esperada,
                               resultado.evolucion.nuevo_nivel, ev.feedback_corto)
            out["evolucion"] = {"nuevo_nivel": resultado.evolucion.nuevo_nivel}
    else:
        card.marcar_fallo()
        escribir_evolucion(card, card.pregunta, card.respuesta,
                           card.nivel_actual, ev.feedback_corto)
        out["xp"] = 0
        out["esperado"] = card.respuesta
    return out


def api_stats():
    from collections import defaultdict
    todas = []
    for p in settings.questions_dir().glob("*.md"):
        c = parse_flashcard(p)
        if c:
            todas.append(c)
    por_area = defaultdict(lambda: {"total": 0, "n1": 0, "n2": 0, "n3": 0, "n4": 0,
                                    "aciertos": 0, "bosses": 0})
    for c in todas:
        a = por_area[c.area]
        a["total"] += 1
        a[f"n{c.nivel_actual}"] += 1
        a["aciertos"] += c.historial_aciertos
        if c.es_boss_battle:
            a["bosses"] += 1
    return {"areas": dict(por_area), "total": len(todas)}


def api_plantar(area, sugerencias):
    from datetime import date
    import re
    questions = settings.questions_dir()
    plantadas = []
    for s in sugerencias:
        cid = re.sub(r"[^a-z0-9_]", "", s["concepto"].lower().replace(" ", "_"))[:40]
        if not cid:
            continue
        path = questions / f"{cid}.md"
        if path.exists():
            continue
        path.write_text(f"""---
id: {cid}
tema: {area}
concepto: {s["concepto"]}
nivel_actual: {int(s.get("nivel", 1))}
estado: activo
proximo_repaso: {date.today().isoformat()}
historial_aciertos: 0
---

# Q: {s["pregunta"]}
**A:** {s["respuesta_esperada"]}
""", encoding="utf-8")
        plantadas.append(cid)
    return {"ok": True, "plantadas": plantadas}


# ─── TEMAS (pausar/activar) ───────────────────────────────────────

def _listar_carpetas_vault(max_nivel=2):
    ignore = {".obsidian", ".git", "templates", "assets", "resources",
              ".trash", "excalidraw", "questions", "evoflash", "venv"}
    vault = settings.vault_path()
    if not vault.exists():
        return []
    rutas = set()
    for p in vault.rglob("*"):
        if not p.is_dir():
            continue
        if any(part.lower() in ignore for part in p.parts):
            continue
        rel = p.relative_to(vault).as_posix()
        if rel.count("/") < max_nivel:
            rutas.add(rel)
    return sorted(rutas)


def api_temas():
    cfg = settings.cargar_temas()
    pausados_l = [p.lower() for p in cfg.get("pausados", [])]
    # Tarjetas por carpeta (todas, no solo pendientes)
    from collections import Counter
    conteo = Counter()
    for p in settings.questions_dir().glob("*.md"):
        c = parse_flashcard(p)
        if c:
            conteo[c.area] += 1
    carpetas = []
    for carp in _listar_carpetas_vault():
        carpetas.append({
            "carpeta": carp,
            "pausada": carp.lower() in pausados_l,
            "tarjetas": conteo.get(carp, 0),
        })
    return {"carpetas": carpetas, "pausados": cfg.get("pausados", [])}


def api_tema_toggle(carpeta, accion):
    cfg = settings.cargar_temas()
    if accion == "pausar" and carpeta not in cfg["pausados"]:
        cfg["pausados"].append(carpeta)
    elif accion == "activar" and carpeta in cfg["pausados"]:
        cfg["pausados"].remove(carpeta)
    elif accion == "reset":
        cfg = {"activos": [], "pausados": []}
    settings.TEMAS_CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "pausados": cfg["pausados"]}


# ─── EXÁMENES ─────────────────────────────────────────────────────

def _examenes_file():
    f = settings.ROOT / "config" / "examenes.json"
    if not f.exists():
        f.write_text(json.dumps({"examenes": []}, ensure_ascii=False), encoding="utf-8")
    return f


def api_examenes():
    return json.loads(_examenes_file().read_text(encoding="utf-8"))


def api_examen_guardar(data):
    f = _examenes_file()
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "total": len(data.get("examenes", []))}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _archivo(self, path: Path, mime: str):
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionAbortedError, BrokenPipeError):
            pass  # navegador canceló (normal, no reportar como bug)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionAbortedError, BrokenPipeError):
            pass

    def do_GET(self):
        # Páginas del juego / menú
        if self.path in ("/", "/index.html"):
            return self._archivo(HERE / "index.html", "text/html; charset=utf-8")
        if self.path == "/menu.html":
            return self._archivo(HERE / "menu.html", "text/html; charset=utf-8")
        if self.path == "/skill_tree.html":
            return self._archivo(HERE / "skill_tree.html", "text/html; charset=utf-8")

        # API JSON
        if self.path.startswith("/api/pending"):
            area = parse_qs(urlparse(self.path).query).get("area", [None])[0]
            return self._json(api_pending(area))
        if self.path.startswith("/api/stats"):
            return self._json(api_stats())
        if self.path.startswith("/api/temas"):
            return self._json(api_temas())
        if self.path.startswith("/api/examenes"):
            return self._json(api_examenes())

        # Archivos estáticos permitidos dentro del dashboard (data.json, imágenes, css, etc)
        clean_path = self.path.lstrip("/")
        static_file = HERE / clean_path
        if static_file.exists() and static_file.is_file():
            mime_map = {".md": "text/markdown", ".json": "application/json",
                        ".html": "text/html; charset=utf-8", ".css": "text/css",
                        ".js": "application/javascript", ".png": "image/png",
                        ".jpg": "image/jpeg", ".svg": "image/svg+xml"}
            mime = mime_map.get(static_file.suffix.lower(), "application/octet-stream")
            return self._archivo(static_file, mime)

        self.send_error(404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json({"ok": False, "error": "body inválido"}, 400)
        try:
            if self.path == "/api/answer":
                # LLM tiene máximo 30s (timeout alto porque Gemini puede tardar 503)
                import time
                try:
                    return self._json(api_answer(body.get("path", ""), body.get("respuesta", "")))
                except RuntimeError as e:
                    traceback.print_exc()
                    # 503 saturado del LLM: fallback rápido en modo MOCK
                    j = get_judge()
                    if j.mock:
                        return self._json({"ok": False, "error": "LLM no disponible"}, 503)
                    mock_response = j._mock_response(
                        "concepto", 1, body.get("respuesta", ""), "respuesta_esperada")
                    return self._json({
                        "ok": True,
                        "correcta": mock_response.evaluacion.es_correcta,
                        "feedback": mock_response.evaluacion.feedback_corto,
                        "sugerencias": [],
                        "xp": 0,
                    })
            elif self.path == "/api/plantar":
                return self._json(api_plantar(body.get("area", "General"),
                                       body.get("sugerencias", [])))
            elif self.path == "/api/tema":
                return self._json(api_tema_toggle(body.get("carpeta", ""),
                                                  body.get("accion", "")))
            elif self.path == "/api/examen_guardar":
                return self._json(api_examen_guardar(body))
            else:
                self.send_error(404)
        except Exception as e:
            traceback.print_exc()
            self._json({"ok": False, "error": str(e)}, 500)


def lanzar():
    server = ThreadingHTTPServer(("127.0.0.1", 8766), Handler)
    print("⚡ EvoFlash Web → http://127.0.0.1:8766")
    print("⚡ Juega directo en el navegador (sin CLI)")
    server.serve_forever()


if __name__ == "__main__":
    lanzar()
