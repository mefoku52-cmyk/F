import os
from typing import List, Dict, Any

def fix_duplicates(project_path: str, duplicate_groups: List[List[str]]) -> Dict[str, Any]:
    result = {"removed": [], "errors": []}
    for group in duplicate_groups:
        if len(group) < 2:
            continue
        for path in group[1:]:
            full_path = os.path.join(project_path, path)
            try:
                if os.path.isfile(full_path):
                    os.remove(full_path)
                    result["removed"].append(path)
            except Exception as e:
                result["errors"].append(f"{path}: {e}")
    return result

def get_deadcode_suggestions(deadcode_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return deadcode_list

def get_dangerous_suggestions(dangerous_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return dangerous_list
