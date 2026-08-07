import json

from sdk.client import ForensicSuiteClient

client = ForensicSuiteClient(history_enabled=False)
result = client.get_scores(project_path=".")

with open("../security_scan_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("SCAN OK")
print(json.dumps(result, ensure_ascii=False, indent=2)[:500])
