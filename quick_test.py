"""Quick test: upload bad_python.py to API and print results."""
import requests, json, sys

resp = requests.post(
    "http://localhost:8000/api/scan",
    files=[("files", ("bad_python.py", open(r"example_files\bad_python.py", "rb")))]
)
data = resp.json()
print(json.dumps({
    "total_issues": len(data.get("issues", [])),
    "security_issues": len([i for i in data.get("issues", []) if i.get("category") == "security"]),
    "complexity_items": len(data.get("complexity", [])),
    "scan_errors": data.get("scan_errors", []),
}, indent=2))

# Print security details
for i in data.get("issues", []):
    if i.get("category") == "security":
        print(f"  SECURITY: [{i['rule']}] {i['message']}")

for c in data.get("complexity", []):
    print(f"  COMPLEXITY: {c['name']} rank={c['rank']} score={c['complexity']}")
