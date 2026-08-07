from pathlib import Path

p = Path("plugins/secrets/plugin.py")

s = p.read_text()

s = s.replace(
    """                      if "docs/tests" not in str(path):
              findings.append(Finding(""",
    """                      ignored_paths = (
                          "docs/tests",
                          "tests/",
                          "fixtures/",
                          "examples/",
                          "example/",
                      )

                      if any(x in str(f.rel_path).lower() for x in ignored_paths):
                          continue

                      findings.append(Finding(""",
)

p.write_text(s)

print("Secrets plugin opraveny")
