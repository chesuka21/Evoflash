"""README — EvoFlash: comandos rápidos para César"""

COMANDOS = """
═══════════════════════════════════════════════════════════════════
  ⚡ COMANDOS EVOFLASH (desde C:\\Users\\cesar\\Desktop\\EVOFLASH\\evoflash)
═══════════════════════════════════════════════════════════════════

🎮 JUGAR (doble click o CMD):
   evoflash.bat                ← proyecto venv (RECOMENDADO)
   evoflash.bat --mock         ← sin API (offline/dev)

📦 GENERAR DECK (modo examen, estudio dirigido):
   venv\\Scripts\\python.exe ingestion\\seed_cards.py \\
       --examen "Security+" \\
       --temario "Firewalls, VPN, IDS/IPS, Criptografía, Phishing" \\
       --nivel 1 --subcarpeta Security_Plus

🏗️ SEMBRAR 3 tarjetas demo (Networking):
   venv\\Scripts\\python.exe ingestion\\seed_demo.py

🧪 CORRER TESTS:
   venv\\Scripts\\python.exe -m pytest tests/ -q

📂 VER VAULT ACTUAL:
   venv\\Scripts\\python.exe -c "from config import settings; print(settings.vault_flashcards_dir())"

═══════════════════════════════════════════════════════════════════
⚙️  CONFIGURAR PERFIL DE ESTUDIO (versión 0.1):
   Edita C:\\Users\\cesar\\Desktop\\EVOFLASH\\evoflash\\perfil_estudio.json
   (se autogenera al correr seed_cards.py — edítalo a tu gusto)
═══════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(COMANDOS)
