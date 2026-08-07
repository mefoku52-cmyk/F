# ForensicSuite v1.0

Modulárna analytická platforma pre softvérové projekty.

## Rýchly štart

```bash
# 1. Nainštaluj (iba skopíruj súbory)
cd ~/projekt_puzzle
cp -r forensicsuite_v1_platform ForensicSuite-v1
cd ForensicSuite-v1

# 2. Otestuj
python3 tests/test_smoke.py

# 3. Skenuj
python3 cli/main.py scan . --formats json,markdown,html

# 4. Spusti server
python3 cli/main.py server --port 8765
```

## Novinky v 1.0

- **Config loading**: `config/default.yaml` je TERAZ načítavaný
- **Nové pluginy**: `secrets`, `shell`, `git`
- **Security skóre**: Už nie je N/A – kombinuje CVE + secrets + shell
- **Cache**: Inkrementálne skeny (rýchlejšie opakované behy)
- **Progress bar**: Vizualizácia behu v CLI
- **HTML report**: Prehľadný dashboard v prehliadači
- **HTTP API**: REST endpointy pre integráciu
- **Exit codes**: 0=OK, 1=error, 2=kritické nálezy (vhodné pre CI/CD)

## Príkazy

```bash
# Sken s custom configom
python3 cli/main.py scan /cesta/k/projektu --config moj_config.yaml

# Sken bez cache
python3 cli/main.py scan . --no-cache

# Verbózny výstup
python3 cli/main.py scan . --verbose

# Iba JSON report
python3 cli/main.py scan . --formats json --output-dir ./report

# API server
python3 cli/main.py server --host 0.0.0.0 --port 8765
```

## API Endpoints

```bash
curl http://localhost:8765/health
curl http://localhost:8765/version
curl -X POST http://localhost:8765/scan \
  -H "Content-Type: application/json" \
  -d '{"path": ".", "formats": ["json", "html"]}'
```

## Štruktúra reportu

```
forensicsuite_report/
├── report.json    # Strojovo čitateľný (CI/CD)
├── report.md      # Pre človeka (PR review)
└── report.html    # Dashboard v prehliadači
```

## Pluginy

| Plugin | Čo analyzuje | Podmienka spustenia |
|--------|-------------|---------------------|
| filesystem | Súbory, duplicity, orphaned images | Vždy |
| python | AST, complexity, dead code, cykly | Prítomnosť .py súborov |
| secrets | API kľúče, tokeny, heslá | Prítomnosť textových súborov |
| shell | Bash skripty, nebezpečné príkazy | Prítomnosť .sh súborov |
| git | Git história, branch, commits | Prítomnosť .git adresára |

## Vývoj

```bash
# Pridaj nový plugin
mkdir plugins/moj
touch plugins/moj/__init__.py
# napíš plugins/moj/plugin.py (dedí z Plugin)

# Otestuj
python3 tests/test_smoke.py
```

## Licencia

MIT – používaj, upravuj, šíri. Žiadne závislosti na treťích stranách
pre základnú funkcionalitu.


## 📊 Badges

[![Tests](https://github.com/mefoku52-cmyk/F/actions/workflows/ci.yml/badge.svg)](https://github.com/mefoku52-cmyk/F/actions)
[![Security](https://img.shields.io/badge/security-95%25-brightgreen)](https://github.com/mefoku52-cmyk/F)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

## 📄 License

MIT License - Copyright (c) 2026 Radoslav Čornanič (mefoku52-cmyk)

Permission is hereby granted, free of charge, to any person obtaining a copy...

## 👤 Author

**Radoslav Čornanič** (mefoku52-cmyk)

- GitHub: [@mefoku52-cmyk](https://github.com/mefoku52-cmyk)
