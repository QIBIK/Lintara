from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import time
import shutil
from scanner import run_ruff_scan

app = FastAPI(title="Python Code Auditor")

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
    return {"message": "Python Code Auditor MVP. Static files missing."}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

from typing import List

@app.post("/api/scan")
async def scan_files(files: List[UploadFile] = File(...)):
    all_issues = []
    
    for file in files:
        # Валидация расширения
        if not file.filename.endswith(".py"):
            continue # Пропускаем не-питоновские файлы или можно кидать ошибку

        # Валидация размера (10MB)
        MAX_SIZE = 10 * 1024 * 1024
        content = await file.read()
        if len(content) > MAX_SIZE:
            continue
        
        # Сброс указателя после чтения
        await file.seek(0)

        # Сохранение временного файла
        timestamp = f"{int(time.time())}_{file.filename}"
        temp_file_path = os.path.join(UPLOAD_DIR, timestamp)
        
        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Запуск сканирования
            result = run_ruff_scan(temp_file_path, original_filename=file.filename)
            
            if result["status"] == "success":
                all_issues.extend(result["issues"])
            
        finally:
            # Удаление временного файла
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    return {
        "status": "success",
        "issues": all_issues,
        "files_scanned": len(files)
    }

# uvicorn main:app --reload
