"""Test del menú web completo: todas las rutas nuevas."""
import json, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
server = subprocess.Popen(
    [sys.executable, "web_dashboard/servidor.py"],
    cwd=str(ROOT),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
time.sleep(3)
try:
    # 1. menu.html carga
    r = urllib.request.urlopen("http://127.0.0.1:8766/menu.html", timeout=5)
    assert r.status == 200
    print("✅ /menu.html →", r.status, len(r.read()), "bytes")

    # 2. API temas
    r = urllib.request.urlopen("http://127.0.0.1:8766/api/temas", timeout=5)
    temas = json.loads(r.read())
    print(f"✅ /api/temas → {len(temas['carpetas'])} carpetas detectadas")
    for t in temas["carpetas"][:3]:
        print(f"   - {t['carpeta']}: {'⏸️' if t['pausada'] else '✅'} ({t['tarjetas']} tarjetas)")

    # 3. Toggle un tema y revertir (no dejarlo pausado después del test)
    primera = temas["carpetas"][0]["carpeta"]
    req = urllib.request.Request(
        "http://127.0.0.1:8766/api/tema",
        data=json.dumps({"carpeta": primera, "accion": "pausar"}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    r = urllib.request.urlopen(req, timeout=5)
    out = json.loads(r.read())
    print(f"✅ /api/tema (pausar {primera}) → pausados: {out['pausados']}")
    # Revertir
    req2 = urllib.request.Request(
        "http://127.0.0.1:8766/api/tema",
        data=json.dumps({"carpeta": primera, "accion": "activar"}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req2, timeout=5)
    print(f"✅ /api/tema (activar {primera}) → revertido")

    # 4. API examenes
    r = urllib.request.urlopen("http://127.0.0.1:8766/api/examenes", timeout=5)
    exs = json.loads(r.read())
    print(f"✅ /api/examenes → {len(exs.get('examenes', []))} exámenes")

    # 5. Guardar examen de prueba
    exs["examenes"] = exs.get("examenes", []) + [{
        "nombre": "TEST API", "fecha": "2026-10-01",
        "areas": ["Networking"], "dificultad": "N1—N2", "notas": "test de servidor"
    }]
    req = urllib.request.Request(
        "http://127.0.0.1:8766/api/examen_guardar",
        data=json.dumps(exs).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    r = urllib.request.urlopen(req, timeout=5)
    print(f"✅ /api/examen_guardar → total: {json.loads(r.read())['total']}")
    # Borrar el de prueba
    del exs["examenes"][-1]
    req = urllib.request.Request(
        "http://127.0.0.1:8766/api/examen_guardar",
        data=json.dumps(exs).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=5)
    print("✅ test examen revertido")

    print("\n🎉 Menú web completo funcionando")
finally:
    server.terminate()
    server.wait(timeout=5)
