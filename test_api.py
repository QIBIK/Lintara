import json, urllib.request

url = "http://localhost:8000/api/scan"
filepath = "/app/example_files/bad_python.py"

# Формируем multipart запрос вручную
boundary = "----TestBoundary123"
filename = "bad_python.py"

with open(filepath, "rb") as f:
    file_data = f.read()

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
    f"Content-Type: application/octet-stream\r\n\r\n"
).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(url, data=body)
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

resp = urllib.request.urlopen(req)
data = json.loads(resp.read())

print(f"Issues total: {len(data['issues'])}")
print(f"Complexity total: {len(data['complexity'])}")

security = [i for i in data["issues"] if i.get("category") == "security"]
print(f"Security issues: {len(security)}")
for s in security:
    print(f"  [{s['rule']}] {s['message']}")

for c in data["complexity"]:
    print(f"  Complexity: {c['name']} rank={c['rank']} score={c['complexity']}")
