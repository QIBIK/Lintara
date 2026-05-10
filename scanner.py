import subprocess
import json
import time
import os
import sys
import re


def run_ruff_scan(file_path: str, original_filename: str = None) -> dict:
    try:
        import shutil
        executable = shutil.which("ruff")
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
            return {"status": "error", "message": result.stderr}

        try:
            issues_data = json.loads(raw_output)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse ruff output"}

        normalized_issues = []
        def get_severity(code):
            critical_codes = ["F821", "E999", "F404"] 
            if code in critical_codes: return "critical"
            prefix = code[0] if code else ""
            if prefix == "E": return "critical"
            return "warning"

        file_lines = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_lines = f.readlines()
        except: pass

        display_filename = original_filename if original_filename else os.path.basename(file_path)

        for issue in issues_data[:500]:
            row = issue.get("location", {}).get("row", 0)
            line_text = file_lines[row-1].strip() if 1 <= row <= len(file_lines) else ""
            normalized_issues.append({
                "file": display_filename,
                "line": row,
                "column": issue.get("location", {}).get("column", 0),
                "rule": issue.get("code", ""),
                "severity": get_severity(issue.get("code", "")),
                "message": issue.get("message", ""),
                "line_text": line_text,
                "category": "style"
            })
        return {"status": "success", "issues": normalized_issues}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_bandit_scan(file_path: str, original_filename: str = None) -> dict:
    try:
        import shutil
        executable = shutil.which("bandit") or "bandit"
        result = subprocess.run([executable, "-f", "json", file_path], capture_output=True, text=True, timeout=30)
        raw_output = result.stdout
        if not raw_output.strip(): return {"status": "success", "issues": []}
        data = json.loads(raw_output)
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
                "line_text": item.get("code", "").strip().split("\n")[0] if item.get("code") else "",
                "category": "security"
            })
        return {"status": "success", "issues": normalized}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_radon_complexity(file_path: str, original_filename: str = None) -> dict:
    try:
        import shutil
        executable = shutil.which("radon") or "radon"
        result = subprocess.run([executable, "cc", "-j", "-n", "B", file_path], capture_output=True, text=True, timeout=30)
        raw_output = result.stdout
        if not raw_output.strip() or raw_output.strip() == "{}": return {"status": "success", "complexity": []}
        data = json.loads(raw_output)
        display_filename = original_filename or os.path.basename(file_path)
        complexity_items = []
        for _, blocks in data.items():
            for block in blocks:
                complexity_items.append({
                    "file": display_filename,
                    "name": block.get("name", "unknown"),
                    "type": block.get("type", "function"),
                    "line": block.get("lineno", 0),
                    "endline": block.get("endline", block.get("lineno", 0)),
                    "complexity": block.get("complexity", 0),
                    "rank": block.get("rank", "A")
                })
        return {"status": "success", "complexity": complexity_items}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_hadolint_scan(file_path: str, original_filename: str = None) -> dict:
    try:
        import shutil
        executable = shutil.which("hadolint") or "hadolint"
        result = subprocess.run([executable, "--format", "json", file_path], capture_output=True, text=True, timeout=30)
        raw_output = result.stdout
        if not raw_output.strip() or raw_output.strip() == "[]": return {"status": "success", "issues": []}
        data = json.loads(raw_output)
        display_filename = original_filename or os.path.basename(file_path)
        normalized = []
        for item in data:
            level = item.get("level", "warning").lower()
            severity = "critical" if level == "error" else ("warning" if level == "warning" else "info")
            normalized.append({
                "file": display_filename, "line": item.get("line", 0), "column": item.get("column", 0),
                "rule": item.get("code", "DL0000"), "severity": severity,
                "message": f"[DOCKER] {item.get('message', '')}", "line_text": "", "category": "docker"
            })
        return {"status": "success", "issues": normalized}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- НОВЫЕ СКАНЕРЫ ---

def run_cppcheck_scan(file_path: str, original_filename: str = None) -> dict:
    """Запуск cppcheck для C/C++ файлов."""
    try:
        # Используем специальный шаблон для легкого парсинга: file:line:severity:id:message
        template = "{file}:{line}:{severity}:{id}:{message}"
        result = subprocess.run(
            ["cppcheck", f"--template={template}", "--enable=all", "--suppress=missingIncludeSystem", file_path],
            capture_output=True, text=True, timeout=30
        )
        
        # Cppcheck выводит ошибки в stderr
        output = result.stderr.strip()
        if not output: return {"status": "success", "issues": []}
        
        normalized = []
        display_filename = original_filename or os.path.basename(file_path)
        
        for line in output.splitlines():
            parts = line.split(":", 4)
            if len(parts) < 5: continue
            
            sev_raw = parts[2].strip()
            severity = "critical" if sev_raw in ["error"] else ("warning" if sev_raw in ["warning", "style", "performance"] else "info")
            
            normalized.append({
                "file": display_filename, "line": int(parts[1]) if parts[1].isdigit() else 0,
                "column": 0, "rule": parts[3], "severity": severity,
                "message": f"[CPP] {parts[4]}", "line_text": "", "category": "style"
            })
        return {"status": "success", "issues": normalized}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_staticcheck_scan(file_path: str, original_filename: str = None) -> dict:
    """Запуск staticcheck для Go файлов."""
    try:
        # staticcheck работает лучше по директориям, но мы запустим для файла
        result = subprocess.run(
            ["staticcheck", "-f", "json", file_path],
            capture_output=True, text=True, timeout=30
        )
        
        output = result.stdout.strip()
        if not output: return {"status": "success", "issues": []}
        
        normalized = []
        display_filename = original_filename or os.path.basename(file_path)
        
        for line in output.splitlines():
            try:
                item = json.loads(line)
                sev_raw = item.get("severity", "warning").lower()
                severity = "critical" if sev_raw == "error" else "warning"
                
                normalized.append({
                    "file": display_filename, "line": item.get("location", {}).get("line", 0),
                    "column": item.get("location", {}).get("column", 0),
                    "rule": item.get("code", "ST0000"), "severity": severity,
                    "message": f"[GO] {item.get('message', '')}", "line_text": "", "category": "style"
                })
            except: continue
        return {"status": "success", "issues": normalized}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_htmlhint_scan(file_path: str, original_filename: str = None) -> dict:
    """Запуск htmlhint для HTML файлов."""
    try:
        result = subprocess.run(["htmlhint", "--format", "json", file_path], capture_output=True, text=True, timeout=30)
        output = result.stdout.strip()
        if not output or output == "[]": return {"status": "success", "issues": []}
        
        data = json.loads(output)
        normalized = []
        display_filename = original_filename or os.path.basename(file_path)
        
        for item in data[0].get("messages", []):
            level = item.get("type", "warning")
            severity = "critical" if level == "error" else "warning"
            normalized.append({
                "file": display_filename, "line": item.get("line", 0), "column": item.get("col", 0),
                "rule": item.get("rule", {}).get("id", "htmlhint"), "severity": severity,
                "message": f"[HTML] {item.get('message', '')}", "line_text": "", "category": "style"
            })
        return {"status": "success", "issues": normalized}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_stylelint_scan(file_path: str, original_filename: str = None) -> dict:
    """Запуск stylelint для CSS файлов."""
    try:
        # Для stylelint нужен конфиг, создадим временный если нет
        result = subprocess.run(
            ["stylelint", file_path, "--formatter", "json", "--config", "/app/.stylelintrc.json"],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if not output: return {"status": "success", "issues": []}
        
        data = json.loads(output)
        normalized = []
        display_filename = original_filename or os.path.basename(file_path)
        
        for file_res in data:
            for item in file_res.get("warnings", []):
                severity = "critical" if item.get("severity") == "error" else "warning"
                normalized.append({
                    "file": display_filename, "line": item.get("line", 0), "column": item.get("column", 0),
                    "rule": item.get("rule", "css-lint"), "severity": severity,
                    "message": f"[CSS] {item.get('text', '')}", "line_text": "", "category": "style"
                })
        return {"status": "success", "issues": normalized}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_yaml_scan(file_path: str, original_filename: str = None):
    try:
        process = subprocess.run(["yamllint", "-f", "parsable", file_path], capture_output=True, text=True)
        issues = []
        output = process.stdout.strip()
        if not output: return {"status": "success", "issues": []}
        for line in output.splitlines():
            parts = line.split(":", 3)
            if len(parts) < 4: continue
            severity = "critical" if "[error]" in parts[3] else "warning"
            normalized_msg = parts[3].replace("[error]", "").replace("[warning]", "").strip()
            issues.append({
                "file": original_filename or file_path, "line": int(parts[1]), "column": int(parts[2]),
                "rule": "yaml", "severity": severity, "message": normalized_msg, "line_text": "", "category": "style"
            })
        return {"status": "success", "issues": issues}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_eslint_scan(file_path: str, original_filename: str = None) -> dict:
    try:
        import shutil
        executable = shutil.which("eslint") or "eslint"
        result = subprocess.run([executable, file_path, "--format", "json"], capture_output=True, text=True, timeout=30)
        raw_output = result.stdout
        if not raw_output.strip(): return {"status": "success", "issues": []}
        data = json.loads(raw_output)
        issues_data = data[0].get("messages", []) if data else []
        normalized_issues = []
        display_filename = original_filename or os.path.basename(file_path)
        for issue in issues_data:
            severity = "critical" if issue.get("severity") == 2 or issue.get("fatal") else "warning"
            normalized_issues.append({
                "file": display_filename, "line": issue.get("line", 0), "column": issue.get("column", 0),
                "rule": issue.get("ruleId") or "LintError", "severity": severity,
                "message": issue.get("message", "Unknown issue"), "line_text": "", "category": "style"
            })
        return {"status": "success", "issues": normalized_issues}
    except Exception as e:
        return {"status": "error", "message": str(e)}
