from pathlib import Path

p = Path("plugins/shell/plugin.py")

backup = Path("plugins/shell/plugin.py.before_exec_fix")
backup.write_text(p.read_text())

s = p.read_text()

s = s.replace(
    '"exec": r"\\bexec\\s",',
    '"exec_shell": r"^\\s*exec\\s+(bash|sh|zsh|python|python3)\\s+-c",',
)

s = s.replace(
    '("eval", "exec", "curl_pipe", "wget_pipe")',
    '("eval", "exec_shell", "curl_pipe", "wget_pipe")',
)

p.write_text(s)

print("OK - shell exec pravidlo upravene")
print("Backup:", backup)
