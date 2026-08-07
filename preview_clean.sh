#!/bin/bash

echo "🔍 PREHĽAD SÚBOROV NA ODSTRÁNENIE"
echo "========================================="
echo ""

# 1. Pomocné skripty
echo "📁 1. POMOCNÉ SKRIPTY (fix*, clean*, *.sh):"
find . -maxdepth 1 -name "fix_*.sh" -type f 2>/dev/null | head -20
find . -maxdepth 1 -name "clean_*.sh" -type f 2>/dev/null | head -20
find . -maxdepth 1 -name "*_fix.sh" -type f 2>/dev/null | head -20
find . -maxdepth 1 -name "continue_fix.sh" -type f 2>/dev/null
find . -maxdepth 1 -name "final_cleanup*.sh" -type f 2>/dev/null
find . -maxdepth 1 -name "fix_waste_platform.sh" -type f 2>/dev/null
echo "   Celkom: $(find . -maxdepth 1 -name "*.sh" -type f 2>/dev/null | wc -l) súborov"

echo ""
echo "📁 2. ZÁLOHOVÉ SÚBORY (*.bak, *.backup):"
find . -name "*.bak" -type f 2>/dev/null | head -10
find . -name "*.backup" -type f 2>/dev/null | head -10
echo "   Celkom: $(find . -name "*.bak" -o -name "*.backup" -type f 2>/dev/null | wc -l) súborov"

echo ""
echo "📁 3. DOČASNÉ REPORTY A LOGY:"
ls -la bandit*.json 2>/dev/null || echo "   Žiadne"
ls -la security_baseline.json 2>/dev/null || echo "   Žiadne"
ls -la safety.json 2>/dev/null || echo "   Žiadne"
ls -la sensitive_audit.txt 2>/dev/null || echo "   Žiadne"
ls -la potential_secrets.txt 2>/dev/null || echo "   Žiadne"
ls -la dead_code*.txt 2>/dev/null || echo "   Žiadne"
ls -la complexity_report.txt 2>/dev/null || echo "   Žiadne"
ls -la cycles.txt 2>/dev/null || echo "   Žiadne"
ls -la .secrets.baseline 2>/dev/null || echo "   Žiadne"

echo ""
echo "📁 4. POMOCNÉ PYTHON SKRIPTY:"
find . -maxdepth 1 -name "fix_*.py" -type f 2>/dev/null
find . -maxdepth 1 -name "repair_*.py" -type f 2>/dev/null
find . -maxdepth 1 -name "run_security_scan.py" -type f 2>/dev/null
find . -maxdepth 1 -name "monitor.py" -type f 2>/dev/null
echo "   Celkom: $(find . -maxdepth 1 -name "fix_*.py" -o -name "repair_*.py" -o -name "run_security_scan.py" -o -name "monitor.py" 2>/dev/null | wc -l) súborov"

echo ""
echo "📁 5. PRÁZDNADE ADRESÁRE:"
find . -type d -empty 2>/dev/null | head -10
echo "   Celkom: $(find . -type d -empty 2>/dev/null | wc -l) adresárov"

echo ""
echo "📁 6. __pycache__ A PYC SÚBORY:"
find . -type d -name "__pycache__" 2>/dev/null | head -10
echo "   Celkom: $(find . -type d -name "__pycache__" 2>/dev/null | wc -l) adresárov"
echo "   PYC súborov: $(find . -name "*.pyc" -type f 2>/dev/null | wc -l)"

echo ""
echo "📁 7. ARCHÍVY A STARÉ REPORTY:"
ls -la *.tar.gz 2>/dev/null || echo "   Žiadne"
ls -la ForensicSuite-v1_STABLE_*.tar.gz 2>/dev/null || echo "   Žiadne"
ls -d forensicsuite_report/ 2>/dev/null || echo "   Žiadne"
ls -d self_audit/ 2>/dev/null || echo "   Žiadne"
ls -d archive/cleanup_*/ 2>/dev/null || echo "   Žiadne"
ls -d archive/disabled_tools/ 2>/dev/null || echo "   Žiadne"

echo ""
echo "📁 8. DIST A REPORT ADRESÁRE:"
ls -d dist/ 2>/dev/null || echo "   Žiadne"
ls -d report.json/ 2>/dev/null || echo "   Žiadne"
ls -d report.md/ 2>/dev/null || echo "   Žiadne"
ls -d report.html/ 2>/dev/null || echo "   Žiadne"

echo ""
echo "========================================="
echo "📊 SÚHRN"
echo "========================================="
TOTAL=$(find . -name "*.bak" -o -name "*.backup" -o -name "fix_*.sh" -o -name "clean_*.sh" -o -name "fix_*.py" -o -name "repair_*.py" -o -name "monitor.py" -o -name "run_security_scan.py" -o -name "bandit*.json" -o -name "safety.json" -o -name "security_baseline.json" -o -name "*.tar.gz" -o -name "*.pyc" -o -type d -name "__pycache__" 2>/dev/null | wc -l)
echo "Celkovo súborov na odstránenie: ~$TOTAL"

echo ""
echo "💡 Ak chceš pokračovať, spusti: ./clean_project.sh"
echo "========================================="
