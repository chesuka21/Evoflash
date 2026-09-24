"""Demo seed — crea un vault de prueba con 3 flashcards"""
from pathlib import Path

DEMO_CARDS = [
    ("ip_001", "Networking", "Dirección IP", 1,
     "¿Qué es una dirección IP?",
     "Identificador numérico único de un dispositivo en una red"),
    ("dns_001", "Networking", "DNS", 1,
     "¿Qué hace el sistema DNS?",
     "Traduce nombres de dominio a direcciones IP"),
    ("http_001", "Networking", "HTTP", 2,
     "¿Qué comando curl hace una petición GET con headers visibles?",
     "curl -v https://ejemplo.com"),
]


def seed_demo_vault(base: Path):
    evo = base / "EvoFlash" / "Networking"
    evo.mkdir(parents=True, exist_ok=True)
    for cid, tema, concepto, nivel, q, a in DEMO_CARDS:
        (evo / f"{cid}.md").write_text(f"""---
id: {cid}
tema: {tema}
concepto: {concepto}
nivel_actual: {nivel}
estado: activo
proximo_repaso: 2026-09-21
historial_aciertos: 0
---

# Q: {q}
**A:** {a}
""", encoding="utf-8")
    print(f"✅ Demo vault creado en {evo}")


if __name__ == "__main__":
    seed_demo_vault(Path(__file__).parent / "demo_vault")
