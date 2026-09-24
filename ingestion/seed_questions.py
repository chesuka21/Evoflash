"""Seed: tarjetas de ejemplo en tu Questions vault (Networking + Cybersecurity)"""
from pathlib import Path
from datetime import date
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

DEMO_CARDS = [
    # Teoría
    {
        "id": "ip_001", "tema": "Networking", "concepto": "Dirección IP", "nivel": 1,
        "pregunta": "¿Qué es una dirección IP?",
        "respuesta": "Identificador numérico único de un dispositivo en una red",
        "practice_cmd": "", "practice_esperada": ""
    },
    {
        "id": "dns_001", "tema": "Networking", "concepto": "DNS", "nivel": 1,
        "pregunta": "¿Qué hace el sistema DNS?",
        "respuesta": "Traduce nombres de dominio a direcciones IP",
        "practice_cmd": "", "practice_esperada": ""
    },
    # PRÁCTICA — comando
    {
        "id": "ipconfig_001", "tema": "Networking", "concepto": "ipconfig", "nivel": 1,
        "pregunta": "Abre tu terminal CMD y ejecuta el comando 'ipconfig'. ¿Qué dirección IP tiene tu máquina ahora mismo?",
        "respuesta": "Debe devolver una dirección IPv4 en el formato 192.168.x.x o 10.x.x.x",
        "practice_cmd": "ipconfig",
        "practice_esperada": "La salida muestra IPv4 Address, Subnet Mask y Default Gateway"
    },
    # PRÁCTICA avanzada — escalamiento
    {
        "id": "curl_001", "tema": "Networking", "concepto": "curl -v", "nivel": 2,
        "pregunta": "Ejecuta 'curl -v https://google.com' y observa los headers. ¿Cuál es el puerto por defecto para HTTPS?",
        "respuesta": "El puerto por defecto para HTTPS es 443, visible en la línea 'Connected to google.com (142.250.x.x) port 443'",
        "practice_cmd": "curl -v https://google.com",
        "practice_esperada": "Debe mostrar la conexión TCP resuelta en el puerto 443 del servidor de Google"
    },
    # BOSS BATTLE — Nivel 4 (rol/troubleshooting)
    {
        "id": "boss_dns_001", "tema": "Networking", "concepto": "Troubleshooting DNS complejo", "nivel": 4,
        "pregunta": """🚨 ALERTA: Un usuario reporta que no puede acceder a google.com.
   - IP: 192.168.1.100 (tu red local)
   - DNS: 8.8.8.8 (Google)
   - El ping a 8.8.8.8 SÍ funciona
   - El ping a google.com NO funciona
   - Otros dispositivos en la misma red SÍ pueden resolver google.com

   Tienes 3 pasos para encontrar la causa raíz. ¿Qué harías?""",
        "respuesta": "1. Probar DNS internos con 'nslookup google.com localhost' — el DNS local podría estar forzando otro registro. 2. Limpiar caché DNS con 'ipconfig /flushdns'. 3. Verificar el archivo hosts o configuración de DNS del router. La causa más probable es un DNS interno forzado o el hosts file adulterado.",
        "practice_cmd": "", "practice_esperada": ""
    },
]


def seed_questions():
    vault = settings.vault_flashcards_dir()
    vault.mkdir(parents=True, exist_ok=True)

    for c in DEMO_CARDS:
        extras = ""
        if c["practice_cmd"]:
            extras += f'practice_cmd: {c["practice_cmd"]}\n'
        if c["practice_esperada"]:
            extras += f'practice_esperada: {c["practice_esperada"]}\n'

        path = vault / f"{c['id']}.md"
        if path.exists():
            print(f"   ⏭️  Ya existe: {c['id']}")
            continue
        contenido = f"""---
id: {c['id']}
tema: {c['tema']}
concepto: {c['concepto']}
nivel_actual: {c['nivel']}
estado: activo
proximo_repaso: {date.today().isoformat()}
historial_aciertos: 0
{extras}---

# Q: {c['pregunta']}
**A:** {c['respuesta']}
"""
        path = vault / f"{c['id']}.md"
        path.write_text(contenido, encoding="utf-8")
        print(f"✅ Creada: {path.name}")

    print(f"\n📂 Vault: {vault}")
    print("🎮 Ejecuta: evoflash.bat")
    print(f"📊 Total tarjetas: {len(DEMO_CARDS)}")


if __name__ == "__main__":
    seed_questions()
