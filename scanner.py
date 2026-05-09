import subprocess
import json
import time
import os

import sys

def run_ruff_scan(file_path: str, original_filename: str = None) -> dict:
    try:
        import shutil
        # 1. Сначала ищем в PATH (самый надежный способ в venv)
        executable = shutil.which("ruff")
        
        # 2. Если не нашли, ищем рядом с питоном
        if not executable:
            python_dir = os.path.dirname(sys.executable)
            ruff_exe = os.path.join(python_dir, "ruff.exe" if os.name == "nt" else "ruff")
            if os.path.exists(ruff_exe):
                executable = ruff_exe

        # 3. Если все еще не нашли, пробуем стандартный путь для venv в текущей папке
        if not executable:
            alt_path = os.path.join(os.getcwd(), "venv", "Scripts", "ruff.exe") if os.name == "nt" else \
                       os.path.join(os.getcwd(), "venv", "bin", "ruff")
            if os.path.exists(alt_path):
                executable = alt_path

        # 4. Последняя надежда - просто строка "ruff"
        if not executable:
            executable = "ruff"

        # Запуск ruff через subprocess
        result = subprocess.run(
            [executable, "check", "--output-format=json", "--select=F,E,W", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Ruff возвращает ненулевой код, если найдены ошибки, поэтому берем stdout в любом случае
        raw_output = result.stdout
        if not raw_output and result.stderr:
            # Если в stdout пусто, но есть stderr, возможно ruff не установлен или ошибка запуска
            if "ruff" in result.stderr.lower():
                return {"status": "error", "message": "Ruff is not installed or not in PATH"}
            return {"status": "error", "message": result.stderr}

        try:
            issues_data = json.loads(raw_output)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse ruff output"}

        normalized_issues = []
        # Маппинг уровней важности
        def get_severity(code):
            # Серьезные ошибки (Undefined name, Syntax errors и т.д.)
            critical_codes = ["F821", "E999", "F404"] 
            if code in critical_codes:
                return "critical"
            
            prefix = code[0] if code else ""
            if prefix == "E": return "critical" # PEP8 Errors usually serious
            if prefix == "F": return "warning"  # Pyflakes (unused imports etc) - now warning
            if prefix == "W": return "warning"
            return "info"

        # Используем оригинальное имя файла, если оно передано, иначе имя временного файла
        display_filename = original_filename if original_filename else os.path.basename(file_path)

        for issue in issues_data[:500]:
            code = issue.get("code", "")
            
            normalized_issues.append({
                "file": display_filename,
                "line": issue.get("location", {}).get("row", 0),
                "column": issue.get("location", {}).get("column", 0),
                "rule": code,
                "severity": get_severity(code),
                "message": issue.get("message", "")
            })

        return {
            "scan_id": str(int(time.time())),
            "issues": normalized_issues,
            "status": "success"
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Scan timed out (30s)"}
    except FileNotFoundError:
        return {"status": "error", "message": f"Ruff executable not found. Tried: {executable}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}
