from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import time
import shutil
from scanner import run_ruff_scan, run_eslint_scan

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

@app.post("/api/scan")
async def scan_files(files: List[UploadFile] = File(...)):
    all_issues = []
    files_processed = 0
    errors = []
    
    for file in files:
        filename = file.filename.lower()
        scanner_func = None
        
        if filename.endswith(".py"):
            scanner_func = run_ruff_scan
        elif filename.endswith(".js"):
            scanner_func = run_eslint_scan
            
        if not scanner_func:
            continue 

        files_processed += 1
        
        MAX_SIZE = 10 * 1024 * 1024
        content = await file.read()
        if len(content) > MAX_SIZE:
            errors.append(f"Файл {file.filename} слишком большой")
            continue
        
        await file.seek(0)

        timestamp = f"{int(time.time())}_{file.filename}"
        temp_file_path = os.path.join(UPLOAD_DIR, timestamp)
        
        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            result = scanner_func(temp_file_path, original_filename=file.filename)
            
            if result["status"] == "success":
                all_issues.extend(result["issues"])
            else:
                # Если сканер вернул ошибку (например, синтаксическую)
                errors.append(f"Ошибка в {file.filename}: {result.get('message', 'Неизвестная ошибка')}")
                # Добавляем системную ошибку в список проблем, чтобы пользователь ее видел
                all_issues.append({
                    "file": file.filename,
                    "line": 0,
                    "column": 0,
                    "rule": "SCAN_ERROR",
                    "severity": "critical",
                    "message": result.get('message', 'Ошибка при анализе файла'),
                    "line_text": ""
                })
            
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    return {
        "status": "success",
        "issues": all_issues,
        "files_scanned": files_processed,
        "scan_errors": errors
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

    # Создаем временную директорию для клонирования
    with tempfile.TemporaryDirectory(dir=UPLOAD_DIR) as tmp_dir:
        try:
            # Клонируем репозиторий (только последний коммит для скорости)
            # Устанавливаем GIT_TERMINAL_PROMPT=0, чтобы git не запрашивал пароль для приватных репо
            process = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, tmp_dir],
                capture_output=True,
                text=True,
                timeout=60
            )

            if process.returncode != 0:
                error_msg = process.stderr
                if "terminal prompts disabled" in error_msg or "Authentication failed" in error_msg:
                    raise HTTPException(status_code=403, detail="Репозиторий приватный или требует авторизации. Поддерживаются только публичные репозитории.")
                raise HTTPException(status_code=400, detail=f"Ошибка при клонировании: {error_msg}")

            # Обходим репозиторий рекурсивно
            path_obj = pathlib.Path(tmp_dir)
            for file_path in path_obj.rglob("*"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    scanner_func = None
                    
                    if ext == ".py":
                        scanner_func = run_ruff_scan
                    elif ext == ".js":
                        scanner_func = run_eslint_scan
                    
                    if scanner_func:
                        files_processed += 1
                        # Относительный путь для красоты в отчете
                        rel_path = str(file_path.relative_to(tmp_dir))
                        
                        result = scanner_func(str(file_path), original_filename=rel_path)
                        
                        if result["status"] == "success":
                            all_issues.extend(result["issues"])
                        else:
                            errors.append(f"Ошибка в {rel_path}: {result.get('message')}")

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=408, detail="Превышено время ожидания клонирования")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Системная ошибка: {str(e)}")

    return {
        "status": "success",
        "issues": all_issues,
        "files_scanned": files_processed,
        "scan_errors": errors
    }
