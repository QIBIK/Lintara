from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import time
import shutil
from scanner import (
    run_ruff_scan, run_eslint_scan, run_yaml_scan,
    run_bandit_scan, run_radon_complexity,
    run_hadolint_scan, run_cppcheck_scan,
    run_staticcheck_scan, run_htmlhint_scan,
    run_stylelint_scan, run_java_scan, run_universal_security_scan
)

app = FastAPI(title="Multi-Language Code Auditor")

UPLOAD_DIR = "uploads"
STATIC_DIR = "static"

for directory in [UPLOAD_DIR, STATIC_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path): return FileResponse(index_path)
    return {"message": "Code Auditor MVP. Static files missing."}

# Расширения, которые мы поддерживаем
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".yaml", ".yml", 
    ".c", ".cpp", ".cc", ".h", ".hpp", # C/C++
    ".go",                             # Go
    ".html", ".htm",                   # HTML
    ".css",                            # CSS
    ".java"                            # Java
}

def get_scanners_for_file(filename: str):
    lower = filename.lower()
    basename = os.path.basename(lower)
    ext = os.path.splitext(lower)[1]
    scanners = []

    if ext == ".py":
        scanners.append(("style", run_ruff_scan))
        scanners.append(("security", run_bandit_scan))
    elif ext == ".js":
        scanners.append(("style", run_eslint_scan))
    elif ext in (".yaml", ".yml"):
        scanners.append(("style", run_yaml_scan))
    elif ext in (".c", ".cpp", ".cc", ".h", ".hpp"):
        scanners.append(("style", run_cppcheck_scan))
    elif ext == ".go":
        scanners.append(("style", run_staticcheck_scan))
    elif ext in (".html", ".htm"):
        scanners.append(("style", run_htmlhint_scan))
    elif ext == ".css":
        scanners.append(("style", run_stylelint_scan))
    elif ext == ".java":
        scanners.append(("style", run_java_scan))
    elif basename == "dockerfile" or basename.startswith("dockerfile."):
        scanners.append(("docker", run_hadolint_scan))

    return scanners

def is_supported_file(filename: str) -> bool:
    lower = filename.lower()
    basename = os.path.basename(lower)
    ext = os.path.splitext(lower)[1]
    return ext in SUPPORTED_EXTENSIONS or basename == "dockerfile" or basename.startswith("dockerfile.")

@app.post("/api/scan")
async def scan_files(files: list[UploadFile] = File(...)):
    all_issues, errors, files_code, all_complexity = [], [], {}, []
    files_processed = 0

    for file in files:
        filename = file.filename
        scanners = get_scanners_for_file(filename)
        if not scanners: continue

        files_processed += 1
        content = await file.read()
        await file.seek(0)
        
        try: files_code[filename] = content.decode("utf-8")
        except: files_code[filename] = "[Binary or Unknown Encoding]"

        timestamp = f"{int(time.time())}_{filename}"
        temp_path = os.path.join(UPLOAD_DIR, timestamp)

        try:
            with open(temp_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
            for category, scanner_func in scanners:
                result = scanner_func(temp_path, original_filename=filename)
                if result["status"] == "success": all_issues.extend(result.get("issues", []))
                else: errors.append(f"Error in {filename}: {result.get('message')}")
            
            # Universal security check for secrets in all files
            sec_res = run_universal_security_scan(temp_path, original_filename=filename)
            if sec_res["status"] == "success": all_issues.extend(sec_res.get("issues", []))
            
            if filename.lower().endswith(".py"):
                cx = run_radon_complexity(temp_path, original_filename=filename)
                if cx["status"] == "success": all_complexity.extend(cx.get("complexity", []))
        finally:
            if os.path.exists(temp_path): os.remove(temp_path)

    return {
        "status": "success", "issues": all_issues, "files_scanned": files_processed,
        "scan_errors": errors, "files_code": files_code, "complexity": all_complexity
    }

@app.post("/api/scan/git")
async def scan_git_repo(request: dict):
    repo_url = request.get("url")
    all_issues, errors, files_code, all_complexity = [], [], {}, []
    files_processed = 0

    import tempfile, pathlib, subprocess
    with tempfile.TemporaryDirectory(dir=UPLOAD_DIR) as tmp_dir:
        try:
            subprocess.run(["git", "clone", "--depth", "1", repo_url, tmp_dir], capture_output=True, timeout=60)
            path_obj = pathlib.Path(tmp_dir)
            for f_path in path_obj.rglob("*"):
                if f_path.is_file():
                    rel_path = str(f_path.relative_to(tmp_dir))
                    if not is_supported_file(rel_path): continue
                    
                    scanners = get_scanners_for_file(rel_path)
                    files_processed += 1
                    try: files_code[rel_path] = f_path.read_text(encoding="utf-8")
                    except: files_code[rel_path] = "[Error reading]"

                    for category, scanner_func in scanners:
                        result = scanner_func(str(f_path), original_filename=rel_path)
                        if result["status"] == "success": all_issues.extend(result.get("issues", []))
                    
                    # Universal security check
                    sec_res = run_universal_security_scan(str(f_path), original_filename=rel_path)
                    if sec_res["status"] == "success": all_issues.extend(sec_res.get("issues", []))
                    
                    if rel_path.lower().endswith(".py"):
                        cx = run_radon_complexity(str(f_path), original_filename=rel_path)
                        if cx["status"] == "success": all_complexity.extend(cx.get("complexity", []))
        except Exception as e: raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "success", "issues": all_issues, "files_scanned": files_processed,
        "scan_errors": errors, "files_code": files_code, "complexity": all_complexity
    }
