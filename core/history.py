import json
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class HistoryManager:
    def __init__(self, db_path: str = "forensicsuite_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                project_path TEXT NOT NULL,
                file_count INTEGER,
                scores_json TEXT,
                findings_json TEXT,
                plugins_json TEXT,
                version TEXT
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_path ON scans(project_path)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON scans(timestamp)")
        conn.commit()
        conn.close()

    def save_scan(self, result: Dict[str, Any]) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO scans (
                timestamp, project_path, file_count,
                scores_json, findings_json, plugins_json, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                int(time.time()),
                result.get("project_path", ""),
                result.get("file_count", 0),
                json.dumps(result.get("scores", {})),
                json.dumps(result.get("findings", [])),
                json.dumps(result.get("plugins", {})),
                result.get("version", ""),
            ),
        )
        scan_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return scan_id

    def get_history(
        self, project_path: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM scans"
        params = []
        if project_path:
            query += " WHERE project_path = ?"
            params.append(project_path)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            data = dict(row)
            data["scores"] = json.loads(data.get("scores_json", "{}"))
            data["findings"] = json.loads(data.get("findings_json", "[]"))
            data["plugins"] = json.loads(data.get("plugins_json", "{}"))
            data["datetime"] = datetime.fromtimestamp(data["timestamp"]).isoformat()
            data.pop("scores_json", None)
            data.pop("findings_json", None)
            data.pop("plugins_json", None)
            result.append(data)
        return result

    def get_all_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.get_history(None, limit)

    def get_stats(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scans")
        total_scans = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT project_path) FROM scans")
        total_projects = cursor.fetchone()[0]
        cursor.execute(
            "SELECT project_path, COUNT(*) as count FROM scans GROUP BY project_path ORDER BY count DESC LIMIT 5"
        )
        top_projects = [
            {"project": row[0], "scans": row[1]} for row in cursor.fetchall()
        ]
        conn.close()
        return {
            "total_scans": total_scans,
            "total_projects": total_projects,
            "top_projects": top_projects,
        }

    def get_trend(self, project_path: str, score_type: str, limit: int = 10) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, scores_json FROM scans WHERE project_path = ? ORDER BY timestamp DESC LIMIT ?",
            (project_path, limit),
        )
        rows = cursor.fetchall()
        conn.close()

        trend = []
        for ts, scores_json in reversed(rows):
            try:
                scores = json.loads(scores_json)
                value = scores.get(score_type)
                if isinstance(value, dict):
                    value = value.get("score")
                if value is not None:
                    trend.append({"timestamp": ts, "score": value})
            except (json.JSONDecodeError, AttributeError, TypeError):
                continue
        return trend
