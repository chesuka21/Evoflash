"""Test del servidor de skill tree"""
import subprocess
import threading
import time
import urllib.request
import sys
from pathlib import Path

server = subprocess.Popen(
    [sys.executable, "-m", "http.server", "8765"],
    cwd=Path("web_dashboard").resolve(),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

time.sleep(2)

try:
    r = urllib.request.urlopen("http://localhost:8765/skill_tree.html", timeout=5)
    print(f"skill_tree.html: status={r.status} bytes={len(r.read())}")
    r2 = urllib.request.urlopen("http://localhost:8765/data.json", timeout=5)
    data = r2.read()
    print(f"data.json: status={r2.status} bytes={len(data)}")
    print(f"✅ Servidor OK — abierto en http://localhost:8765")
except Exception as e:
    print(f"❌ ERROR: {e}")
finally:
    server.terminate()
    server.wait()
    print("Server detenido")
