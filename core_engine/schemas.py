"""Schema Pydantic — contrato estricto con el LLM"""
from pydantic import BaseModel, Field, field_validator


class Evaluacion(BaseModel):
    es_correcta: bool
    feedback_corto: str = Field(min_length=5, max_length=1500)


class Evolucion(BaseModel):
    nuevo_nivel: int = Field(ge=2, le=4)
    nueva_pregunta: str = Field(min_length=10)
    nueva_respuesta_esperada: str = Field(min_length=5)


class Sugerencia(BaseModel):
    """Tarjeta hermana relacionada que el LLM recomienda sembrar"""
    concepto: str = Field(min_length=3)
    pregunta: str = Field(min_length=10)
    respuesta_esperada: str = Field(min_length=5)
    nivel: int = Field(ge=1, le=4, default=1)


class LLMOutput(BaseModel):
    evaluacion: Evaluacion
    evolucion: Evolucion | None = None  # None si no es correcta
    sugerencias: list[Sugerencia] = []  # tarjetas hermanas del mismo tema

    @field_validator("evolucion")
    @classmethod
    def evolucion_requerida_si_correcta(cls, v, info):
        if info.data.get("evaluacion") and info.data["evaluacion"].es_correcta and v is None:
            raise ValueError("Si es_correcta=True, evolucion es requerida")
        return v
