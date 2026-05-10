from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import time
import shutil
from scanner import (
    run_ruff_scan, run_eslint_scan, run_yaml_scan,
    run_bandit_scan, run_radon_complexity,
    run_hadolint_scan
)

app = FastAPI(title="Multi-Language Code Auditor")

# Директории для статики и загрузок
UPLOAD_DIR = "uploads"
STATIC_DIR = "static"

for directory in [UPLOAD_DIR, STATIC_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Code Auditor MVP. Static files missing."}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

from typing import List

# Расширения, которые мы поддерживаем
SUPPORTED_EXTENSIONS = {".py", ".js", ".yaml", ".yml", ".tf"}

# Имена файлов, которые мы поддерживаем напрямую (без расширения)
SUPPORTED_FILENAMES = {"dockerfile"}


def get_scanners_for_file(filename: str):
    """Возвращает список (scanner_func, category) для данного файла."""
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
    elif basename == "dockerfile" or basename.startswith("dockerfile."):
        scanners.append(("docker", run_hadolint_scan))

    return scanners


def is_supported_file(filename: str) -> bool:
    lower = filename.lower()
    basename = os.path.basename(lower)
    ext = os.path.splitext(lower)[1]
    return ext in SUPPORTED_EXTENSIONS or basename == "dockerfile" or basename.startswith("dockerfile.")


@app.post("/api/scan")
async def scan_files(files: List[UploadFile] = File(...)):
    all_issues = []
    files_processed = 0
    errors = []
    files_code = {}
    all_complexity = []

    for file in files:
        filename = file.filename
        scanners = get_scanners_for_file(filename)

        if not scanners:
            continue

        files_processed += 1

        MAX_SIZE = 10 * 1024 * 1024
        content = await file.read()
        if len(content) > MAX_SIZE:
            errors.append(f"Файл {filename} слишком большой")
            continue

        await file.seek(0)

        try:
            files_code[filename] = content.decode("utf-8")
        except:
            files_code[filename] = "[Не удалось прочитать содержимое файла]"

        timestamp = f"{int(time.time())}_{filename}"
        temp_file_path = os.path.join(UPLOAD_DIR, timestamp)

        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Запускаем все сканеры для файла
            for category, scanner_func in scanners:
                result = scanner_func(temp_file_path, original_filename=filename)
                if result["status"] == "success":
                    all_issues.extend(result.get("issues", []))
                else:
                    errors.append(f"Ошибка в {filename} ({category}): {result.get('message', 'Неизвестная ошибка')}")

            # Цикломатическая сложность для Python
            if filename.lower().endswith(".py"):
                cx_result = run_radon_complexity(temp_file_path, original_filename=filename)
                if cx_result["status"] == "success":
                    all_complexity.extend(cx_result.get("complexity", []))

        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    return {
        "status": "success",
        "issues": all_issues,
        "files_scanned": files_processed,
        "scan_errors": errors,
        "files_code": files_code,
        "complexity": all_complexity
    }


from pydantic import BaseModel
import subprocess
import tempfile
import pathlib

class GitScanRequest(BaseModel):
    url: str

@app.post("/api/scan/git")
async def scan_git_repo(request: GitScanRequest):
    repo_url = request.url
    all_issues = []
    files_processed = 0
    errors = []
    files_code = {}
    all_complexity = []

    with tempfile.TemporaryDirectory(dir=UPLOAD_DIR) as tmp_dir:
        try:
            process = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, tmp_dir],
                capture_output=True,
                text=True,
                timeout=60,
                env={"GIT_TERMINAL_PROMPT": "0", "PATH": os.environ.get("PATH", "")}
            )

            if process.returncode != 0:
                error_msg = process.stderr
                if "terminal prompts disabled" in error_msg or "Authentication failed" in error_msg:
                    raise HTTPException(status_code=403, detail="Репозиторий приватный или требует авторизации.")
                raise HTTPException(status_code=400, detail=f"Ошибка при клонировании: {error_msg}")

            path_obj = pathlib.Path(tmp_dir)
            for file_path in path_obj.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(tmp_dir))

                    if not is_supported_file(rel_path):
                        continue

                    scanners = get_scanners_for_file(rel_path)
                    if not scanners:
                        continue

                    files_processed += 1

                    try:
                        files_code[rel_path] = file_path.read_text(encoding="utf-8")
                    except:
                        files_code[rel_path] = "[Ошибка чтения]"

                    for category, scanner_func in scanners:
                        result = scanner_func(str(file_path), original_filename=rel_path)
                        if result["status"] == "success":
                            all_issues.extend(result.get("issues", []))
                        else:
                            errors.append(f"Ошибка в {rel_path} ({category}): {result.get('message')}")

                    # Complexity для Python
                    if rel_path.lower().endswith(".py"):
                        cx_result = run_radon_complexity(str(file_path), original_filename=rel_path)
                        if cx_result["status"] == "success":
                            all_complexity.extend(cx_result.get("complexity", []))

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=408, detail="Превышено время ожидания клонирования")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Системная ошибка: {str(e)}")

    return {
        "status": "success",
        "issues": all_issues,
        "files_scanned": files_processed,
        "scan_errors": errors,
        "files_code": files_code,
        "complexity": all_complexity
    }
