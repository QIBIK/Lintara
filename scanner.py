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

        # Читаем содержимое файла для извлечения строк с ошибками
        file_lines = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_lines = f.readlines()
        except Exception:
            pass # Если не удалось прочитать, просто не будет текста строки

        # Используем оригинальное имя файла, если оно передано, иначе имя временного файла
        display_filename = original_filename if original_filename else os.path.basename(file_path)

        for issue in issues_data[:500]:
            code = issue.get("code", "")
            row = issue.get("location", {}).get("row", 0)
            
            # Извлекаем текст строки (row - 1, так как в ruff нумерация с 1)
            line_text = ""
            if 1 <= row <= len(file_lines):
                line_text = file_lines[row-1].strip()

            normalized_issues.append({
                "file": display_filename,
                "line": row,
                "column": issue.get("location", {}).get("column", 0),
                "rule": code,
                "severity": get_severity(code),
                "message": issue.get("message", ""),
                "line_text": line_text
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

def run_eslint_scan(file_path: str, original_filename: str = None) -> dict:
    try:
        import shutil
        executable = shutil.which("eslint")
        
        if not executable:
            # Попробуем найти в стандартных путях npm
            if os.name == "nt":
                executable = shutil.which("eslint.cmd")
            
        if not executable:
            return {"status": "error", "message": "ESLint not found. Make sure it is installed (npm install -g eslint)"}

        # Запуск eslint через subprocess с выводом в JSON
        # Используем встроенный форматтер json
        result = subprocess.run(
            [executable, file_path, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        raw_output = result.stdout
        raw_error = result.stderr

        # Если в stdout пусто, но в stderr есть что-то - это системная ошибка запуска
        if not raw_output.strip() and raw_error:
            return {"status": "error", "message": raw_error}

        try:
            # ESLint может вывести предупреждения перед JSON, если запущен не в чистом окружении
            # Пытаемся найти начало JSON массива
            json_start = raw_output.find('[')
            if json_start != -1:
                data = json.loads(raw_output[json_start:])
            else:
                data = json.loads(raw_output)
            
            issues_data = data[0].get("messages", []) if data else []
        except (json.JSONDecodeError, IndexError) as e:
            # Если не удалось распарсить JSON, возвращаем ошибку
            return {"status": "error", "message": f"Failed to parse ESLint output: {str(e)}"}

        normalized_issues = []
        display_filename = original_filename if original_filename else os.path.basename(file_path)

        def get_severity(sev_level, fatal=False):
            if fatal: return "critical"
            if sev_level == 2: return "critical"
            if sev_level == 1: return "warning"
            return "info"

        file_lines = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_lines = f.readlines()
        except Exception:
            pass

        for issue in issues_data:
            line = issue.get("line", 0)
            line_text = ""
            if 1 <= line <= len(file_lines):
                line_text = file_lines[line-1].strip()

            rule_id = issue.get("ruleId")
            if not rule_id:
                rule_id = "SyntaxError" if issue.get("fatal") else "LintError"

            normalized_issues.append({
                "file": display_filename,
                "line": line,
                "column": issue.get("column", 0),
                "rule": rule_id,
                "severity": get_severity(issue.get("severity", 0), issue.get("fatal")),
                "message": issue.get("message", "Unknown issue"),
                "line_text": line_text
            })

        return {
            "scan_id": str(int(time.time())),
            "issues": normalized_issues,
            "status": "success"
        }


    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "ESLint scan timed out"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected ESLint error: {str(e)}"}

