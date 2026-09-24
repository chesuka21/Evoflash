"""Servidor EvoFlash — sirve el index.html y termina."""
import http.server, threading, time, urllib.request

class EvoHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

server = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 8766),
    lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory="web_dashboard", **k),
)
print("⚡ EvoFlash Web → http://127.0.0.1:8766/")
server.serve_forever()
