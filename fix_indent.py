from pathlib import Path

p = Path("plugins/secrets/plugin.py")

lines = p.read_text().splitlines()

new = []

for line in lines:
    if line.startswith("                        ignored_paths"):
        line = "                      ignored_paths = ("

    elif line.startswith('                            "docs/tests"'):
        line = '                          "docs/tests",'

    elif line.startswith('                            "tests/"'):
        line = '                          "tests/",'

    elif line.startswith('                            "fixtures/"'):
        line = '                          "fixtures/",'

    elif line.startswith('                            "examples/"'):
        line = '                          "examples/",'

    elif line.startswith('                            "example/"'):
        line = '                          "example/",'

    elif line.strip() == ")" and 50 < len(new) < 70:
        line = "                      )"

    elif line.startswith("                        if any(x in str(f.rel_path)"):
        line = "                      if any(x in str(f.rel_path).lower() for x in ignored_paths):"

    elif line.strip() == "continue":
        line = "                          continue"

    elif line.startswith("                        findings.append(Finding("):
        line = "                      findings.append(Finding("

    new.append(line)

p.write_text("\n".join(new) + "\n")

print("HOTOVO")
