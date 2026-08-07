from pathlib import Path

p = Path("plugins/filesystem/plugin.py")

if not p.exists():
    print("filesystem plugin nenájdeny")
    exit()

s = p.read_text()

s = s.replace(
    "if file.stat().st_size == 0:",
    'if file.stat().st_size == 0 and file.name not in ["__init__.py"] and "__pycache__" not in str(file):',
)

p.write_text(s)

print("filesystem filter upraveny")
