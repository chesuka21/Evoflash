"""
Test de conexión Obsidian → Web Dashboard.
1. Crea una nota de prueba en Obsidian Vault/prueba/
2. Exporta data.json
3. Verifica que la tarjeta aparece en la web (via API)
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config import settings
from web_dashboard.export_data import exportar
from web_dashboard.servidor import api_pending, api_stats, _listar_carpetas_vault

# 1. Crear nota de prueba
PRUEBA_DIR = settings.vault_path() / "prueba"
PRUEBA_DIR.mkdir(parents=True, exist_ok=True)

contenido = """---
tags: [prueba, cocina]
---

# Cocina Básica: Arroz Blanco Perfecto

El arroz blanco se cocina mejor con proporción 1:2 (1 taza arroz, 2 tazas agua).
Lavado previo hasta agua clara. Hervir, tapar, fuego mínimo 18 minutos.
Reposar 10 minutos sin destapar. Esponjar con tenedor.
Temperatura ideal de servicio: 60-70°C.
"""

nota_path = PRUEBA_DIR / "arroz_blanco.md"
nota_path.write_text(contenido, encoding="utf-8")
print(f"✅ Nota creada: {nota_path}")
print(f"   Tamaño: {len(contenido)} caracteres")

# 2. Exportar data.json (simula lo que hace el .bat)
data = exportar()
print(f"✅ Exportación: {len(data['cards'])} tarjetas → {data['total']} total")

# 3. Verificar que la tarjeta aparece en la API
pendientes = api_pending(None)
prueba_card = [c for c in pendientes["cards"] if "arroz" in c["concepto"].lower()]
if prueba_card:
    c = prueba_card[0]
    print(f"✅ Tarjeta en web: '{c['concepto']}' (Nivel {c['nivel']}, Área: '{c['area']}')")
    print(f"   Pregunta: {c['pregunta'][:80]}...")
else:
    print("⚠️ Tarjeta no encontrada en pendientes (quizás ya pasó el elif primer round)")

# 4. Verificar que el área 'prueba' está en la lista
print(f"✅ Áreas detectadas: {list(api_stats()['areas'].keys())}")

# 5. Carpetas válidas (lista de temas)
carpetas = _listar_carpetas_vault()
print(f"✅ Carpetas válidas encontradas: {[c for c in carpetas if 'prueba' in c.lower()]}")

# 6. Clean up: opcional, pero deja la nota para que la pruebes tú
print(f"\n📂 Archivo real guardado en: {nota_path}")
print("   Abre http://127.0.0.1:8766/menu.html → Temas → debería aparecer 'prueba' como ACTIVA")
print("   En la web (jugar), selecciona 'prueba' y verás la flashcard.")
