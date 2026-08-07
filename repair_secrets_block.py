from pathlib import Path

p = Path("plugins/secrets/plugin.py")

lines = p.read_text().splitlines()

out = []
skip = False

for i, line in enumerate(lines):
    if 'if "docs/tests" not in str(path):' in line:
        skip = True

        out.extend(
            [
                "                      ignored_paths = (",
                '                          "docs/tests",',
                '                          "tests/",',
                '                          "fixtures/",',
                '                          "examples/",',
                '                          "example/",',
                "                      )",
                "",
                "                      if any(x in str(f.rel_path).lower() for x in ignored_paths):",
                "                          continue",
                "",
            ]
        )
        continue

    if skip:
        if "findings.append(Finding(" in line:
            skip = False
            out.append(line)
        continue

    out.append(line)

p.write_text("\n".join(out) + "\n")

print("blok opraveny")
