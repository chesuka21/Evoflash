"""Smoke test del servidor web EvoFlash (endpoints + HTML + respuesta en vivo)."""
import subprocess, threading, time, urllib.request, urllib.error, json, sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
server = subprocess.Popen(
    [sys.executable, str(ROOT / "web_dashboard" / "servidor.py")],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
time.sleep(2)

try:
    # 1. Página principal
    r = urllib.request.urlopen("http://127.0.0.1:8766/", timeout=5)
    print(f"✅ / → {r.status} ({len(r.read())} bytes)")

    # 2. API pending
    r = urllib.request.urlopen("http://127.0.0.1:8766/api/pending", timeout=5)
    data = json.loads(r.read())
    print(f"✅ /api/pending → {len(data['cards'])} pendientes, áreas: {data['areas']}")

    # 3. API stats
    r = urllib.request.urlopen("http://127.0.0.1:8766/api/stats", timeout=5)
    stats = json.loads(r.read())
    print(f"✅ /api/stats → {stats['total']} tarjetas, {len(stats['areas'])} áreas")

    # 4. Evaluar respuesta real con Gemini (la 1ra pendiente)
    if data['cards']:
        c = data['cards'][0]
        req = urllib.request.Request(
            "http://127.0.0.1:8766/api/answer",
            data=json.dumps({"path": c["path"], "respuesta": "no sé bien, eso es como la dirección de una casa"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        r = urllib.request.urlopen(req, timeout=60)
        ans = json.loads(r.read())
        print(f"✅ /api/answer → correcta={ans.get('correcta')} xp={ans.get('xp')} feedback_len={len(ans.get('feedback',''))}")

except Exception as e:
    print(f"❌ FALLA: {e}")
    sys.exit(1)
finally:
    server.terminate()
    server.wait(timeout=5)
