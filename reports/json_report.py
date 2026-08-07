import json
from typing import Any, Dict


def generate(result: Dict[str, Any], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
