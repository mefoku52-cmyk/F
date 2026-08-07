import os
import sys

sys.path.insert(0, os.getcwd())

api_path = "server/api.py"

with open(api_path, "r") as f:
    content = f.read()

# Odstráň automatický sken z run_server
old_run = """def run_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    global _last_result
    # Automatický sken pri štarte
    try:
        print("🔄 Spúšťam automatický sken...")
        _scan_project(".", ["json"])
        print("✅ Automatický sken dokončený")
    except Exception as e:
        print(f"⚠️ Automatický sken zlyhal: {e}")
    server = HTTPServer((host, port), _Handler)
    print(f"ForensicSuite API beží na http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nServer ukončený.")
        server.shutdown()"""

new_run = """def run_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    global _last_result
    # Automatický sken pri štarte – spustíme v samostatnom vlákne
    import threading
    def auto_scan():
        try:
            print("🔄 Spúšťam automatický sken na pozadí...")
            _scan_project(".", ["json"])
            print("✅ Automatický sken dokončený")
        except Exception as e:
            print(f"⚠️ Automatický sken zlyhal: {e}")
    threading.Thread(target=auto_scan, daemon=True).start()
    server = HTTPServer((host, port), _Handler)
    print(f"ForensicSuite API beží na http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nServer ukončený.")
        server.shutdown()"""

if old_run in content:
    content = content.replace(old_run, new_run)
    with open(api_path, "w") as f:
        f.write(content)
    print("✅ server/api.py upravený – automatický sken na pozadí")
else:
    print("⚠️ Pôvodný kód nebol nájdený, skúšam alternatívu...")
    # Ak sa nenájde, pridáme import threading a upravíme
    if "import threading" not in content:
        content = content.replace("import json", "import json\nimport threading")
    # Nájdeme run_server a upravíme ho manuálne (jednoduchšie)
    import re

    pattern = r'def run_server\(host: str = "0.0.0.0", port: int = 8765\) -> None:.*?server\.shutdown\(\)'
    # Použijeme novú verziu
    new_func = """def run_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    global _last_result
    import threading
    def auto_scan():
        try:
            print("🔄 Spúšťam automatický sken na pozadí...")
            _scan_project(".", ["json"])
            print("✅ Automatický sken dokončený")
        except Exception as e:
            print(f"⚠️ Automatický sken zlyhal: {e}")
    threading.Thread(target=auto_scan, daemon=True).start()
    server = HTTPServer((host, port), _Handler)
    print(f"ForensicSuite API beží na http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nServer ukončený.")
        server.shutdown()"""
    content = re.sub(pattern, new_func, content, flags=re.DOTALL)
    with open(api_path, "w") as f:
        f.write(content)
    print("✅ server/api.py upravený (regex)")

print("")
print("Teraz reštartuj API server:")
print("  pkill -f 'server.api'")
print(
    "  python3 -c 'from server.api import run_server; run_server(host=\"0.0.0.0\", port=8765)'"
)
