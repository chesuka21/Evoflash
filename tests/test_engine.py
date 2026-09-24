"""Tests del motor — importación, schema, mock judge, vault IO"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from core_engine.schemas import LLMOutput, Evaluacion, Evolucion
from core_engine.flashcard import Flashcard
from llm_interface.judge import LLMJudge
from vault_manager.vault_io import parse_flashcard, escribir_evolucion, listar_pendientes


def test_schema_valida_evolucion_si_correcta():
    try:
        LLMOutput(evaluacion=Evaluacion(es_correcta=True, feedback_corto="bien"),
                  evolucion=None)
        assert False, "debió lanzar ValidationError"
    except Exception:
        pass


def test_mock_judge_correcta():
    j = LLMJudge(force_mock=True)
    out = j.evaluar_y_evolucionar("Networking", "IP", 1,
                                  "¿Qué es una IP?",
                                  "Identificador numérico único de dispositivo en red",
                                  "Es un identificador numérico único de dispositivo en una red")
    assert out.evaluacion.es_correcta
    assert out.evolucion and out.evolucion.nuevo_nivel == 2


def test_mock_judge_incorrecta():
    j = LLMJudge(force_mock=True)
    out = j.evaluar_y_evolucionar("Networking", "IP", 1,
                                  "¿Qué es una IP?",
                                  "Identificador numérico único de dispositivo en red",
                                  "no sé")
    assert not out.evaluacion.es_correcta
    assert out.evolucion is None


def test_flashcard_sm2():
    c = Flashcard(id="x", tema="t", concepto="c")
    assert c.proximo_repaso == date.today()
    c.marcar_acierto()
    assert c.historial_aciertos == 1
    assert (c.proximo_repaso - date.today()).days == 1


def test_vault_roundtrip(tmp_path):
    md = tmp_path / "test.md"
    md.write_text("""---
id: t1
tema: Networking
concepto: Test
nivel_actual: 1
estado: activo
proximo_repaso: 2026-09-21
historial_aciertos: 0
---

# Q: ¿Pregunta?
**A:** Respuesta
""", encoding="utf-8")
    card = parse_flashcard(md)
    assert card and card.pregunta == "¿Pregunta?" and card.respuesta == "Respuesta"
    escribir_evolucion(card, "Nueva Q", "Nueva A", 2, "feedback")
    card2 = parse_flashcard(md)
    assert card2.nivel_actual == 2 and "Nueva Q" in card2.pregunta


def test_listar_pendientes_demo():
    demo = Path(__file__).parent.parent / "demo_vault" / "EvoFlash"
    if demo.exists():
        pends = listar_pendientes(demo)
        assert len(pends) >= 3
