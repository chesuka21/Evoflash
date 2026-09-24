"""Config loader for EvoFlash"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent  # paquete raíz evoflash/
load_dotenv(ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
VAULT_PATH = Path(os.getenv("VAULT_PATH", ""))
EVOFLASH_FOLDER = os.getenv("EVOFLASH_FOLDER", "EvoFlash")

def vault_path() -> Path:
    """Ruta raíz del vault"""
    return VAULT_PATH

def questions_dir() -> Path:
    """Subcarpeta 'Questions' dentro del vault (donde viven las flashcards)"""
    return VAULT_PATH / EVOFLASH_FOLDER

def vault_flashcards_dir() -> Path:
    """Alias legacy"""
    return questions_dir()

def has_api_key() -> bool:
    return bool(GEMINI_API_KEY)


# ===== Gestión de áreas de estudio (activas / pausadas) =====
# Edita config/temas_estudio.json a mano o con `evoflash_temas.bat`
import json as _json

TEMAS_CONFIG = ROOT / "config" / "temas_estudio.json"


def cargar_temas() -> dict:
    """Devuelve {'activos': [...], 'pausados': [...]}.
    - Si 'activos' está vacío -> todas las carpetas del vault son válidas.
    - Carpetas en 'pausados' se ignoran siempre."""
    if TEMAS_CONFIG.exists():
        try:
            cfg = _json.loads(TEMAS_CONFIG.read_text(encoding="utf-8"))
            return {"activos": cfg.get("activos", []),
                    "pausados": cfg.get("pausados", [])}
        except Exception:
            pass
    return {"activos": [], "pausados": []}


def tema_esta_activo(areasub: str) -> bool:
    """Coincidencia por prefijo y case-insensitive.
    Ej: pausar 'Cursos/Technical Support Fundamentals' excluye también
    'Cursos/Technical Support Fundamentals/Modulo 1/...'"""
    cfg = cargar_temas()
    if not areasub:
        return True
    areasub = areasub.lower().rstrip("/")
    # Excluir si coincide con carpeta pausada
    for p in cfg["pausados"]:
        p = p.lower().rstrip("/")
        if areasub == p or areasub.startswith(p + "/"):
            return False
    # Si hay lista activa, solo incluir las que coincidan
    if not cfg["activos"]:
        return True
    for a in cfg["activos"]:
        a = a.lower().rstrip("/")
        if areasub == a or areasub.startswith(a + "/"):
            return True
    return False
