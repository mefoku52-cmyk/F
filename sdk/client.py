import os
from typing import Any, Dict, List, Optional

from core.config_loader import load_config
from core.engine import ForensicEngine


class ForensicSuiteClient:
    """
    Jednoduchý klient pre programové použitie ForensicSuite.

    Príklad:
        from forensicsuite_sdk import ForensicSuiteClient

        client = ForensicSuiteClient()
        result = client.scan("/path/to/project")
        print(result["scores"])
    """

    def __init__(self, config_path: Optional[str] = None, history_enabled: bool = True):
        """
        Inicializuje klienta.

        Args:
            config_path: Cesta ku konfiguračnému súboru (YAML/JSON).
            history_enabled: Či sa má ukladať história skenov.
        """
        self.config = load_config(config_path)
        self.history_enabled = history_enabled
        self.engine = ForensicEngine(
            config=self.config,
            history_enabled=history_enabled,
        )

    def scan(self, project_path: str, save_history: bool = True) -> Dict[str, Any]:
        """
        Spustí sken projektu a vráti výsledok.

        Args:
            project_path: Cesta k projektu.
            save_history: Či sa má sken uložiť do histórie.

        Returns:
            Kompletný výsledok skenu.
        """
        return self.engine.run(project_path, save_history=save_history)

    def scan_and_report(
        self,
        project_path: str,
        output_dir: str = "forensicsuite_report",
        formats: Optional[List[str]] = None,
        save_history: bool = True,
    ) -> Dict[str, Any]:
        """
        Spustí sken a vygeneruje reporty.

        Args:
            project_path: Cesta k projektu.
            output_dir: Výstupný priečinok pre reporty.
            formats: Zoznam formátov (json, markdown, html).
            save_history: Či sa má sken uložiť do histórie.

        Returns:
            Kompletný výsledok skenu.
        """
        if formats is None:
            formats = ["json", "markdown", "html"]

        result = self.scan(project_path, save_history=save_history)

        os.makedirs(output_dir, exist_ok=True)

        from reports import json_report, markdown_report, html_report

        fmt_map = {
            "json": json_report,
            "markdown": markdown_report,
            "html": html_report,
        }

        for fmt in formats:
            if fmt in fmt_map:
                out_path = os.path.join(output_dir, f"report.{fmt}")
                fmt_map[fmt].generate(result, out_path)

        return result

    def get_scores(
        self, project_path: str, save_history: bool = False
    ) -> Dict[str, Any]:
        """
        Vráti iba skóre (rýchla verzia bez reportov).

        Args:
            project_path: Cesta k projektu.
            save_history: Či sa má sken uložiť do histórie.

        Returns:
            Slovník so skóre.
        """
        result = self.scan(project_path, save_history=save_history)
        return result.get("scores", {})

    def get_history(
        self, project_path: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Vráti históriu skenov pre daný projekt.

        Args:
            project_path: Cesta k projektu (voliteľné).
            limit: Maximálny počet záznamov.

        Returns:
            Zoznam historických záznamov.
        """
        if not self.history_enabled:
            return []
        return self.engine.get_history(project_path, limit)

    def get_trend(
        self, project_path: str, metric: str = "maintainability"
    ) -> List[Dict[str, Any]]:
        """
        Vráti trend pre danú metriku.

        Args:
            project_path: Cesta k projektu.
            metric: Názov metriky (maintainability, architecture, security).

        Returns:
            Zoznam bodov trendu.
        """
        if not self.history_enabled:
            return []
        return self.engine.get_trend(project_path, metric)

    def get_stats(self) -> Dict[str, Any]:
        """
        Vráti štatistiky z histórie.

        Returns:
            Slovník so štatistikami.
        """
        if not self.history_enabled:
            return {}
        return self.engine.get_stats()
