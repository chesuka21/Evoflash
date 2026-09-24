"""Interfaz LLM — Gemini Pro con fallback a MOCK para dev local"""
import json
import os
from google import genai
from core_engine.schemas import LLMOutput, Evaluacion, Evolucion, Sugerencia
from config import settings

# Candidatos de modelo en orden de velocidad/demanda:
# si uno da 503, salta al siguiente automáticamente.
MODELOS = [
    os.getenv("LLM_MODEL", "gemini-3.1-flash-lite"),      # default: rápido, popular pero menos demanda
    "gemini-3.1-flash-lite",                             # mismo del .env por si acaso
    "gemini-3.5-flash",                                   # fallback: menos popular, más estable
    "gemini-3.5-flash-lite",                             # más ligero, menos demanda
    "gemini-3.1-pro",                                   # más pesado pero robusto
]
# Eliminar duplicados preservando orden
_vistos = set()
MODELOS = [m for m in MODELOS if not (m in _vistos or _vistos.add(m))]
_tiempo_desde_ultimo_503 = {}


SYSTEM_PROMPT = """Eres un Motor de Aprendizaje Adaptativo EXIGENTE, experto en {tema}. Tu misión: evaluar respuestas con rigor de examinador profesional y forzar al estudiante a argumentar, no solo definir.

NIVELES DE DIFICULTAD:
- Nivel 1 (Teoría): Definiciones básicas.
- Nivel 2 (Práctica): Cómo ejecutar o aplicar el concepto.
- Nivel 3 (Troubleshooting): Resolver un problema que involucra el concepto.
- Nivel 4 (Avanzado): Escenarios complejos, de seguridad o arquitectura.

REGLAS DE EVALUACIÓN (sé estricto):
1. Une analogías SOLO si capturan la esencia técnica completa. Una analogía parcial = INCORRECTA.
2. La respuesta debe cubrir los puntos clave de la 'Respuesta Esperada'. Si omite un punto crítico, marca INCORRECTA.
3. Respuestas vagas tipo "lo revisaría" sin pasos concretos = INCORRECTA.

REGLAS DE FEEDBACK (OBLIGATORIO, siempre detallado):
- feedback_corto debe tener 3-6 líneas con EXACTAMENTE esta estructura:
  ✅ Aciertos: qué hizo bien (cita sus palabras)
  ❌ Vacíos: qué omitió o dijo impreciso
  🎯 Exige más: qué debería haber argumentado (ej. "debiste mencionar el comando exacto y cómo interpretarías la salida")
  ⚡ Reto: UNA pregunta de profundización que extienda el concepto

REGLAS DE EVOLUCIÓN:
- Si CORRECTA: genera la flashcard del SIGUIENTE NIVEL sobre el mismo 'Concepto Base' y que exija argumentación.
- Si INCORRECTA: evolucion = null.
- En 'sugerencias' incluye 1-2 tarjetas hermanas de conceptos relacionados del mismo tema.

Responde ÚNICAMENTE en JSON válido:
{{
  "evaluacion": {{"es_correcta": true|false, "feedback_corto": "✅ ...\\n❌ ...\\n🎯 ...\\n⚡ ..."}},
  "evolucion": {{"nuevo_nivel": 2|3|4, "nueva_pregunta": "...", "nueva_respuesta_esperada": "..."}} | null,
  "sugerencias": [{{"concepto": "...", "pregunta": "...", "respuesta_esperada": "...", "nivel": 1}}]
}}
"""


def _user_prompt(concepto: str, nivel: int, pregunta: str, respuesta_esperada: str,
                 respuesta_usuario: str) -> str:
    return f"""Concepto Base: {concepto}
Nivel Actual: {nivel}
Pregunta Actual: {pregunta}
Respuesta Esperada: {respuesta_esperada}
Respuesta del Usuario: "{respuesta_usuario}"

Analiza y genera el JSON."""


class LLMJudge:
    def __init__(self, force_mock: bool = False):
        self.mock = force_mock or not settings.has_api_key()
        self.client = None
        if not self.mock:
            from google import genai as google_genai
            self.client = google_genai.Client(api_key=settings.GEMINI_API_KEY)

    def evaluar_y_evolucionar(self, tema: str, concepto: str, nivel: int,
                              pregunta: str, respuesta_esperada: str,
                              respuesta_usuario: str) -> LLMOutput:
        if self.mock:
            return self._mock_response(concepto, nivel, respuesta_usuario, respuesta_esperada)
        return self._gemini_multi_modelo(tema, concepto, nivel, pregunta, respuesta_esperada, respuesta_usuario)

    # ---------- MULTI-MODELO (anti-503) ----------
    def _gemini_multi_modelo(self, tema, concepto, nivel, pregunta, resp_esp, resp_usr) -> LLMOutput:
        prompt = SYSTEM_PROMPT.format(tema=tema) + "\n\n" + _user_prompt(
            concepto, nivel, pregunta, resp_esp, resp_usr)

        for modelo in MODELOS:
            try:
                r = self.client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config={"response_mime_type": "application/json",
                            "temperature": 0.3,
                            "max_output_tokens": 1200},
                )
                try:
                    raw = "".join(p.text for p in r.candidates[0].content.parts
                                  if getattr(p, "text", None))
                except (IndexError, AttributeError):
                    raw = r.text or ""
                data = json.loads(raw)
                return LLMOutput(**data)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"LLM devolvió JSON inválido en {modelo}: {e}")
            except Exception as e:
                err = str(e).lower()
                if "503" in err or "unavailable" in err or "high demand" in err or "overload" in err:
                    continue  # saltamos al siguiente modelo
                if "404" in err:  # modelo no existe en esta API key
                    continue
                raise RuntimeError(f"LLM {modelo} falló: {e}")

        raise RuntimeError(f"Ningún modelo Gemini respondió (todos saturados). Desconecta un rato — en horas pico Gemini aguanta ~1500 RPM por API key.")

    # ---------- MOCK para dev sin API key ----------
    def _mock_response(self, concepto, nivel, respuesta_usuario, respuesta_esperada) -> LLMOutput:
        """Simulación determinista: si la respuesta contiene palabras clave de la esperada, es correcta."""
        palabras_clave = {w.lower().strip(".,;:") for w in respuesta_esperada.split() if len(w) > 3}
        palabras_user = {w.lower().strip(".,;:") for w in respuesta_usuario.split()}
        overlap = len(palabras_clave & palabras_user)
        es_correcta = overlap >= max(1, len(palabras_clave) // 3)

        evolucion = None
        if es_correcta and nivel < 4:
            evolucion = Evolucion(
                nuevo_nivel=nivel + 1,
                nueva_pregunta=f"[MOCK NIVEL {nivel+1}] Aplica '{concepto}' en un escenario práctico real.",
                nueva_respuesta_esperada=f"[MOCK] Demostración práctica de {concepto}.",
            )
        sugerencias = [
            Sugerencia(concepto=f"{concepto} avanzado", pregunta=f"¿Cómo funciona '{concepto}' bajo carga extrema?", respuesta_esperada="[MOCK] Respuesta de ejemplo.", nivel=min(nivel + 1, 4)),
        ] if es_correcta else []
        return LLMOutput(
            evaluacion=Evaluacion(
                es_correcta=es_correcta,
                feedback_corto="[MOCK] Respuesta validada por overlap léxico." if es_correcta
                               else "[MOCK] No detecté conceptos clave. Revisa la teoría.",
            ),
            evolucion=evolucion,
            sugerencias=sugerencias,
        )
