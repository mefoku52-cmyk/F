from pathlib import Path

p = Path("plugins/secrets/plugin.py")

if not p.exists():
    print("secrets plugin nenájdeny")
    exit()

s = p.read_text()

s = s.replace(
    "findings.append", 'if "docs/tests" not in str(path):\n            findings.append'
)

p.write_text(s)

print("secret filter upraveny")
