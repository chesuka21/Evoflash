"""Flashcard model — unidad de datos de Obsidian"""
import re
from pydantic import BaseModel, Field
from datetime import date, timedelta


class Flashcard(BaseModel):
    id: str
    tema: str
    concepto: str
    nivel_actual: int = Field(ge=1, le=4, default=1)
    estado: str = "activo"
    proximo_repaso: date = Field(default_factory=date.today)
    historial_aciertos: int = 0
    pregunta: str = ""
    respuesta: str = ""
    path: str = ""  # ruta al .md

    # Campos nuevos para práctica / imágenes ─────────────
    practice_cmd: str = ""                # Comando a ejecutar (modo Practice)
    practice_esperada: str = ""           # Salida esperada simplificada
    imagen_pregunta: str = ""             # URL o ruta relativa al .md
    imagen_respuesta: str = ""
    carpeta: str = ""                     # subcarpeta en Questions/ (ej. "Networking")
    fuente: str = ""                      # ruta del apunte original (ej. "Cursos/Redes/nota.md")

    @property
    def area(self) -> str:
        """Área de estudio = ruta de subcarpetas del APUNTE ORIGINAL (hasta 2 niveles).
        Ej: 'Cursos/Google cybersecurity' en vez de solo 'Cursos'.
        Fallback: tema si no hay fuente registrada."""
        if not self.fuente:
            return self.tema or "General"
        parts = re.split(r"[/\\]", self.fuente.replace("\\\\", "/"))
        parts = [p for p in parts if p]
        if not parts:
            return self.tema or "General"
        return "/".join(parts[:2]) if len(parts) > 1 else parts[0]

    @property
    def es_boss_battle(self) -> bool:
        """Nivel 4 = Boss Battle (rol/troubleshooting)"""
        return self.nivel_actual == 4 and self.estado == "activo"

    def marcar_acierto(self):
        self.historial_aciertos += 1
        # SM-2 simplificado: intervalos exponenciales
        intervalos = {1: 1, 2: 3, 3: 7, 4: 14}
        dias = intervalos.get(min(self.historial_aciertos, 4), 30)
        self.proximo_repaso = date.today() + timedelta(days=dias)

    def marcar_fallo(self):
        # Degradación de nivel (mecánica de daño)
        if self.nivel_actual > 2:
            self.nivel_actual -= 1
        self.proximo_repaso = date.today() + timedelta(days=1)
