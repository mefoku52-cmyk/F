import os
import sys

sys.path.insert(0, os.getcwd())

# Oprava server/api.py – správne spracovanie findings
api_path = "server/api.py"

with open(api_path, "r") as f:
    content = f.read()

# Pôvodná chybná časť
old_code = """        elif self.path == "/fix/duplicates":
            if not _last_result:
                self._send_json({"error": "Žiadny predošlý sken"}, 400)
                return
            fs_data = _last_result.get("plugins", {}).get("filesystem", {}).get("data", {})
            duplicates = fs_data.get("duplicate_groups", [])"""

new_code = """        elif self.path == "/fix/duplicates":
            if not _last_result:
                self._send_json({"error": "Žiadny predošlý sken"}, 400)
                return
            # Získame findings z filesystem pluginu
            fs_plugin = _last_result.get("plugins", {}).get("filesystem", {})
            if fs_plugin.get("status") == "ok":
                data = fs_plugin.get("data", [])
                if isinstance(data, list):
                    # Hľadáme Finding s duplicitami
                    duplicates = []
                    for f in data:
                        if f.get("message", "").startswith("Duplicitné súbory"):
                            duplicates.append(f.get("metadata", {}).get("duplicate_group", []))
                    # Ak sme nenašli v metadata, skúsime alternatívny spôsob
                    if not duplicates:
                        # Starší formát: priamo v data
                        fs_data = _last_result.get("plugins", {}).get("filesystem", {}).get("data", {})
                        if isinstance(fs_data, dict):
                            duplicates = fs_data.get("duplicate_groups", [])
                else:
                    duplicates = data.get("duplicate_groups", [])
            else:
                duplicates = []"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(api_path, "w") as f:
        f.write(content)
    print("✅ Opravené: /fix/duplicates endpoint")
else:
    print("⚠️ Pôvodný kód nebol nájdený, skúšam alternatívnu opravu...")
    # Alternatívna oprava – nájsť a nahradiť
    import re

    pattern = r'fs_data = _last_result\.get\("plugins", \{\}\)\.get\("filesystem", \{\}\)\.get\("data", \{\}\))\s+duplicates = fs_data\.get\("duplicate_groups", \[\]\)'
    if re.search(pattern, content):
        content = re.sub(
            pattern,
            """fs_data = _last_result.get("plugins", {}).get("filesystem", {}).get("data", {})
            # Ak je fs_data list, extrahujeme duplicity z findings
            if isinstance(fs_data, list):
                duplicates = []
                for f in fs_data:
                    if f.get("message", "").startswith("Duplicitné súbory"):
                        dup_group = f.get("metadata", {}).get("duplicate_group", [])
                        if dup_group:
                            duplicates.append(dup_group)
            else:
                duplicates = fs_data.get("duplicate_groups", [])""",
            content,
        )
        with open(api_path, "w") as f:
            f.write(content)
        print("✅ Opravené (regex)")
    else:
        print("❌ Nepodarilo sa nájsť chybný kód – skontroluj manuálne")

print("")
print("Reštartuj API server:")
print("  pkill -f 'server.api'")
print(
    "  python3 -c 'from server.api import run_server; run_server(host=\"0.0.0.0\", port=8765)'"
)
