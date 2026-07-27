# ForensicSuite v1.0 – Architektúra

## Prehľad

ForensicSuite je modulárna analytická platforma pre softvérové projekty.
Jadro (core) je oddelené od analyzátorov (plugins). Každý plugin implementuje
abstraktnú triedu `Plugin` a je dynamicky objavený za behu.

## Komponenty

```
core/
  engine.py          -> Orchestrátor celého behu
  config_loader.py   -> Načítavanie YAML/JSON configu s fallbackom
  cache.py           -> File-based cache pre AST výsledky
  collector.py       -> Zber súborov s exclude/include patternami
  plugin_manager.py  -> Dynamický discovery + základné rozhranie Plugin
  scheduler.py       -> Izolované spúšťanie pluginov s progress callbackom
  parser.py          -> Bezpečné čítanie textových súborov
  cve_checker.py    -> OSV.dev integrácia (batch + paralelné detaily)

plugins/
  filesystem/        -> Analýza súborového systému (duplicity, orphaned images)
  python/            -> AST analýza Python kódu (complexity, dead code, cykly)
  secrets/           -> Detekcia hardcoded secrets, API kľúčov, tokenov
  shell/             -> Analýza shell skriptov (nebezpečné príkazy)
  git/               -> Analýza git repozitára (branch, commits, uncommitted)

scoring/
  maintainability.py -> Skóre udržovateľnosti
  architecture.py    -> Skóre architektúry
  security.py        -> Skóre bezpečnosti (CVE + secrets + shell)

reports/
  json_report.py     -> Strojovo čitateľný JSON
  markdown_report.py -> Čitateľný Markdown
  html_report.py     -> Statický HTML dashboard

cli/
  main.py            -> argparse CLI (scan, server)

server/
  api.py             -> HTTP API (stdlib only)

tests/
  test_smoke.py      -> Smoke + unit testy
```

## Dátový tok

1. `cli/main.py` parsuje argumenty
2. `core/engine.py` načíta config cez `config_loader.py`
3. `core/collector.py` zozbiera súbory
4. `core/plugin_manager.py` objaví pluginy
5. `core/scheduler.py` spustí každý plugin izolovane
6. `scoring/*.py` agreguje výsledky do skóre
7. `reports/*.py` serializuje do zvoleného formátu

## Rozšírenie – Nový plugin

```python
# plugins/moj/plugin.py
from core.plugin_manager import Plugin
from core.collector import FileInfo
from typing import Any, Dict, List

class MojPlugin(Plugin):
    @property
    def name(self) -> str:
        return "moj"

    def supports(self, project_path: str, files: List[FileInfo]) -> bool:
        return any(f.ext == ".moj" for f in files)

    def analyze(self, project_path: str, files: List[FileInfo]) -> Dict[str, Any]:
        return {"pocet": len([f for f in files if f.ext == ".moj"])}
```

Plugin sa automaticky objaví pri ďalšom behu. Žiadna zmena v jadre.

## Bezpečnostné aspekty

- Každý plugin beží v izolácii – pád jedného nezastaví ostatné
- `safe_read_text()` odmietne binárne súbory a príliš veľké súbory
- `secrets` plugin neukladá celé match-e do reportu (len snippet)
- Cache používa hash mtime+size, nie obsah (rýchlejšie, bez leaku dát)
- API server beží na localhost, bez autentifikácie (pre lokálne použitie)

## Známe obmedzenia

- CVE kontrola funguje iba pre `requirements.txt` vo formáte `name==version`
- Git plugin vyžaduje `git` CLI v PATH
- HTML report je statický (žiadny JS framework)
- Server nemá autentifikáciu (určený pre lokálny development)

