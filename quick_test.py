import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_interface.judge import LLMJudge

j = LLMJudge()
print("Asking Gemini...", flush=True)
out = j.evaluar_y_evolucionar(
    tema="Networking", concepto="DNS", nivel=1,
    pregunta="¿Qué hace el sistema DNS?",
    respuesta_esperada="Traduce nombres de dominio a direcciones IP",
    respuesta_usuario="Traduce nombres de dominio a direcciones IP",
)
print(out.model_dump_json(indent=2))
