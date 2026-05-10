import subprocess
import json
import time
import os
import sys


def run_ruff_scan(file_path: str, original_filename: str = None) -> dict:
    try:
        import shutil
        executable = shutil.which("ruff")
        
        if not executable:
            python_dir = os.path.dirname(sys.executable)
            ruff_exe = os.path.join(python_dir, "ruff.exe" if os.name == "nt" else "ruff")
            if os.path.exists(ruff_exe):
                executable = ruff_exe

        if not executable:
            alt_path = os.path.join(os.getcwd(), "venv", "Scripts", "ruff.exe") if os.name == "nt" else \
                       os.path.join(os.getcwd(), "venv", "bin", "ruff")
            if os.path.exists(alt_path):
                executable = alt_path

        if not executable:
            executable = "ruff"

        result = subprocess.run(
            [executable, "check", "--output-format=json", "--select=F,E,W", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        raw_output = result.stdout
        if not raw_output and result.stderr:
            if "ruff" in result.stderr.lower():
                return {"status": "error", "message": "Ruff is not installed or not in PATH"}
            return {"status": "error", "message": result.stderr}

        try:
            issues_data = json.loads(raw_output)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse ruff output"}

        normalized_issues = []
        def get_severity(code):
            critical_codes = ["F821", "E999", "F404"] 
            if code in critical_codes:
                return "critical"
            prefix = code[0] if code else ""
            if prefix == "E": return "critical"
            if prefix == "F": return "warning"
            if prefix == "W": return "warning"
            return "info"

        file_lines = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_lines = f.readlines()
        except Exception:
            pass

        display_filename = original_filename if original_filename else os.path.basename(file_path)

        for issue in issues_data[:500]:
            code = issue.get("code", "")
            row = issue.get("location", {}).get("row", 0)
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
                "line_text": line_text,
                "category": "style"
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
        return {"status": "error", "message": f"Ошибка запуска Ruff: {str(e)}"}


def run_bandit_scan(file_path: str, original_filename: str = None) -> dict:
    """Запуск Bandit для поиска уязвимостей в Python-коде."""
    try:
        import shutil
        executable = shutil.which("bandit")
        if not executable:
            executable = "bandit"

        result = subprocess.run(
            [executable, "-f", "json", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        raw_output = result.stdout
        if not raw_output.strip():
            # Bandit может ничего не найти — это нормально
            return {"status": "success", "issues": []}

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse Bandit output"}

        display_filename = original_filename or os.path.basename(file_path)
        normalized = []

        for item in data.get("results", []):
            sev = item.get("issue_severity", "LOW")
            severity = "critical" if sev == "HIGH" else ("warning" if sev == "MEDIUM" else "info")
            normalized.append({
                "file": display_filename,
                "line": item.get("line_number", 0),
                "column": 0,
                "rule": item.get("test_id", "B000"),
                "severity": severity,
                "message": f"[SECURITY] {item.get('issue_text', '')}",
                "line_text": (item.get("code", "").strip().split("\n")[0] if item.get("code") else ""),
                "category": "security"
            })

        return {"status": "success", "issues": normalized}

    except FileNotFoundError:
        return {"status": "error", "message": "Bandit not found. Install: pip install bandit"}
    except Exception as e:
        return {"status": "error", "message": f"Bandit error: {str(e)}"}


def run_semgrep_scan(file_path: str, original_filename: str = None) -> dict:
    """Запуск Semgrep для поиска уязвимостей (SQL-инъекции, хардкод секретов и т.д.)."""
    try:
        import shutil
        executable = shutil.which("semgrep")
        if not executable:
            executable = "semgrep"

        result = subprocess.run(
            [executable, "scan", "--config", "auto", "--json", "--quiet", file_path],
            capture_output=True,
            text=True,
            timeout=120
        )

        raw_output = result.stdout
        if not raw_output.strip():
            return {"status": "success", "issues": []}

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse Semgrep output"}

        display_filename = original_filename or os.path.basename(file_path)
        normalized = []

        for item in data.get("results", []):
            sev_raw = item.get("extra", {}).get("severity", "WARNING").upper()
            severity = "critical" if sev_raw == "ERROR" else ("warning" if sev_raw == "WARNING" else "info")
            rule_id = item.get("check_id", "semgrep-rule")
            # Сокращаем длинные rule_id от semgrep
            if "." in rule_id:
                rule_id = rule_id.split(".")[-1]

            normalized.append({
                "file": display_filename,
                "line": item.get("start", {}).get("line", 0),
                "column": item.get("start", {}).get("col", 0),
                "rule": rule_id,
                "severity": severity,
                "message": f"[VULN] {item.get('extra', {}).get('message', '')}",
                "line_text": item.get("extra", {}).get("lines", "").strip().split("\n")[0],
                "category": "security"
            })

        return {"status": "success", "issues": normalized}

    except FileNotFoundError:
        return {"status": "error", "message": "Semgrep not found. Install: pip install semgrep"}
    except Exception as e:
        return {"status": "error", "message": f"Semgrep error: {str(e)}"}


def run_radon_complexity(file_path: str, original_filename: str = None) -> dict:
    """Расчёт цикломатической сложности Python-функций через radon."""
    try:
        import shutil
        executable = shutil.which("radon")
        if not executable:
            executable = "radon"

        result = subprocess.run(
            [executable, "cc", "-j", "-n", "B", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        raw_output = result.stdout
        if not raw_output.strip() or raw_output.strip() == "{}":
            return {"status": "success", "complexity": []}

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse radon output"}

        display_filename = original_filename or os.path.basename(file_path)
        complexity_items = []

        for fpath, blocks in data.items():
            for block in blocks:
                rank = block.get("rank", "A")
                complexity = block.get("complexity", 0)
                name = block.get("name", "unknown")
                block_type = block.get("type", "function")
                lineno = block.get("lineno", 0)
                endline = block.get("endline", lineno)

                complexity_items.append({
                    "file": display_filename,
                    "name": name,
                    "type": block_type,
                    "line": lineno,
                    "endline": endline,
                    "complexity": complexity,
                    "rank": rank
                })

        return {"status": "success", "complexity": complexity_items}

    except FileNotFoundError:
        return {"status": "error", "message": "Radon not found. Install: pip install radon"}
    except Exception as e:
        return {"status": "error", "message": f"Radon error: {str(e)}"}


def run_hadolint_scan(file_path: str, original_filename: str = None) -> dict:
    """Запуск hadolint для проверки Dockerfile."""
    try:
        import shutil
        executable = shutil.which("hadolint")
        if not executable:
            executable = "hadolint"

        result = subprocess.run(
            [executable, "--format", "json", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        raw_output = result.stdout
        if not raw_output.strip() or raw_output.strip() == "[]":
            return {"status": "success", "issues": []}

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse hadolint output"}

        display_filename = original_filename or os.path.basename(file_path)
        normalized = []

        for item in data:
            level = item.get("level", "warning").lower()
            severity = "critical" if level == "error" else ("warning" if level == "warning" else "info")
            normalized.append({
                "file": display_filename,
                "line": item.get("line", 0),
                "column": item.get("column", 0),
                "rule": item.get("code", "DL0000"),
                "severity": severity,
                "message": f"[DOCKER] {item.get('message', '')}",
                "line_text": "",
                "category": "docker"
            })

        return {"status": "success", "issues": normalized}

    except FileNotFoundError:
        return {"status": "error", "message": "hadolint not found"}
    except Exception as e:
        return {"status": "error", "message": f"hadolint error: {str(e)}"}


def run_yaml_scan(file_path: str, original_filename: str = None):
    """Запуск yamllint для проверки YAML файлов"""
    try:
        # -f parsable выдает удобный формат для парсинга
        process = subprocess.run(
            ["yamllint", "-f", "parsable", file_path],
            capture_output=True,
            text=True
        )
        
        issues = []
        filename = original_filename or file_path
        
        # yamllint выводит ошибки даже если returncode != 0
        output = process.stdout.strip()
        if not output:
            return {"status": "success", "issues": []}

        for line in output.splitlines():
            # Формат: file:line:col: [level] message (rule)
            parts = line.split(":", 3)
            if len(parts) < 4: continue
            
            # parts[1] - line, parts[2] - col, parts[3] - [level] message (rule)
            line_num = int(parts[1])
            col_num = int(parts[2])
            msg_part = parts[3].strip()
            
            severity = "warning"
            if "[error]" in msg_part: severity = "critical"
            
            # Очищаем сообщение от [error] или [warning]
            clean_msg = msg_part.replace("[error]", "").replace("[warning]", "").strip()
            
            # Извлекаем правило (оно в конце в скобках)
            rule = "yaml-style"
            if "(" in clean_msg and clean_msg.endswith(")"):
                rule_start = clean_msg.rfind("(")
                rule = clean_msg[rule_start+1:-1]
                clean_msg = clean_msg[:rule_start].strip()

            issues.append({
                "file": filename,
                "line": line_num,
                "column": col_num,
                "rule": rule,
                "severity": severity,
                "message": clean_msg,
                "line_text": "",
                "category": "style"
            })

        return {"status": "success", "issues": issues}
    except Exception as e:
        return {"status": "error", "message": f"Ошибка запуска yamllint: {str(e)}"}


def run_eslint_scan(file_path: str, original_filename: str = None) -> dict:
    try:
        import shutil
        executable = shutil.which("eslint")
        
        if not executable:
            if os.name == "nt":
                executable = shutil.which("eslint.cmd")
            
        if not executable:
            return {"status": "error", "message": "ESLint not found. Make sure it is installed (npm install -g eslint)"}

        result = subprocess.run(
            [executable, file_path, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        raw_output = result.stdout
        raw_error = result.stderr

        if not raw_output.strip() and raw_error:
            return {"status": "error", "message": raw_error}

        try:
            json_start = raw_output.find('[')
            if json_start != -1:
                data = json.loads(raw_output[json_start:])
            else:
                data = json.loads(raw_output)
            
            issues_data = data[0].get("messages", []) if data else []
        except (json.JSONDecodeError, IndexError) as e:
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
                "line_text": line_text,
                "category": "style"
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
