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
            # E999 is syntax error, F821 is undefined name - these are CRITICAL
            critical_codes = ["E999", "F821", "F404", "F823", "F822"] 
            if code in critical_codes: return "critical"
            
            # F401 (Unused import), F541 (F-string without placeholders) are warnings
            if code in ["F401", "F541"]: return "warning"
            
            # E-prefix (mostly PEP8) should be warnings by default
            if code.startswith("E"): return "warning"
            
            # F-prefix (logical errors) should be critical
            if code.startswith("F"): return "critical"
            
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
    """Запуск htmlhint для HTML файлов с предварительной очисткой шаблонов."""
    try:
        temp_lint_path = file_path + ".lint.html"
        is_template = False
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "{%" in content or "{{" in content:
                    is_template = True
                    # Заменяем блоки шаблона на пробелы, сохраняя длину, чтобы не сбить колонки
                    cleaned = re.sub(r'\{%.*?%\}', lambda m: " " * len(m.group(0)), content, flags=re.DOTALL)
                    cleaned = re.sub(r'\{\{.*?\}\}', lambda m: " " * len(m.group(0)), cleaned, flags=re.DOTALL)
                    with open(temp_lint_path, "w", encoding="utf-8") as tf:
                        tf.write(cleaned)
                else:
                    import shutil
                    shutil.copy2(file_path, temp_lint_path)
        except:
            temp_lint_path = file_path

        result = subprocess.run(["htmlhint", "--format", "json", temp_lint_path], capture_output=True, text=True, timeout=30)
        
        # Удаляем временный файл для линтинга
        if temp_lint_path != file_path and os.path.exists(temp_lint_path):
            os.remove(temp_lint_path)

        output = result.stdout.strip()
        if not output or output == "[]": return {"status": "success", "issues": []}
        
        data = json.loads(output)
        normalized = []
        display_filename = original_filename or os.path.basename(file_path)
        
        for item in data[0].get("messages", []):
            rule_id = item.get("rule", {}).get("id", "")
            level = item.get("type", "warning")
            
            # Если это шаблон, игнорируем отсутствие doctype
            if is_template and rule_id == "doctype-first":
                continue
                
            severity = "critical" if level == "error" else "warning"
            
            normalized.append({
                "file": display_filename, "line": item.get("line", 0), "column": item.get("col", 0),
                "rule": rule_id or "htmlhint", "severity": severity,
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
            # Special case: style issues should be warning
            if "(line-length)" in parts[3]: severity = "warning"
            if "(new-lines)" in parts[3]: severity = "warning"
            if "(document-start)" in parts[3]: severity = "warning"
            
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

def run_java_scan(file_path: str, original_filename: str = None) -> dict:
    """Basic Java scanner using javac for syntax and regex for common issues."""
    try:
        display_filename = original_filename or os.path.basename(file_path)
        issues = []
        
        # 1. Syntax check with javac
        # Note: javac needs .java extension to work properly in some cases
        syntax_res = subprocess.run(["javac", "-Xlint", file_path], capture_output=True, text=True, timeout=30)
        if syntax_res.returncode != 0:
            # Parse javac output: file:line: error: message
            for line in syntax_res.stderr.splitlines():
                match = re.search(r':(\d+):\s+(error|warning):\s+(.*)', line)
                if match:
                    line_num = int(match.group(1))
                    sev = "critical" if match.group(2) == "error" else "warning"
                    msg = match.group(3)
                    issues.append({
                        "file": display_filename, "line": line_num, "column": 0,
                        "rule": "JAVA-SYNTAX", "severity": sev,
                        "message": f"[JAVA] {msg}", "line_text": "", "category": "style"
                    })

        # 2. Custom Regex Checks
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for i, text in enumerate(lines):
                    line_no = i + 1
                    # Line length
                    if len(text) > 100:
                        issues.append({
                            "file": display_filename, "line": line_no, "column": 0,
                            "rule": "JAVA-E501", "severity": "warning",
                            "message": "[JAVA] Line too long (>100 chars)", "line_text": text.strip(), "category": "style"
                        })
                    # Hardcoded password
                    if re.search(r'(password|passwd|secret|pwd)\s*=\s*["\'].*["\']', text, re.I):
                        issues.append({
                            "file": display_filename, "line": line_no, "column": 0,
                            "rule": "JAVA-SEC", "severity": "critical",
                            "message": "[JAVA] Possible hardcoded password", "line_text": text.strip(), "category": "security"
                        })
                    # System.out.println
                    if "System.out.println" in text:
                        issues.append({
                            "file": display_filename, "line": line_no, "column": 0,
                            "rule": "JAVA-STYLE", "severity": "warning",
                            "message": "[JAVA] Use a logger instead of System.out.println", "line_text": text.strip(), "category": "style"
                        })
        except: pass

        return {"status": "success", "issues": issues}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_universal_security_scan(file_path: str, original_filename: str = None) -> dict:
    """Universal scanner to find secrets, API keys and sensitive data in any file."""
    try:
        display_filename = original_filename or os.path.basename(file_path)
        issues = []
        
        # Patterns for secrets
        patterns = [
            (r'(?i)api_key\s*[:=]\s*["\'][a-z0-9-]{20,}["\']', "Potential API Key"),
            (r'(?i)secret\s*[:=]\s*["\'][a-z0-9-]{20,}["\']', "Potential Secret"),
            (r'(?i)bearer\s+[a-z0-9._-]{20,}', "Potential Bearer Token"),
            (r'-----BEGIN (RSA|EC|PGP|OPENSSH) PRIVATE KEY-----', "Private Key exposed"),
            (r'postgres://[a-zA-Z0-9:]+:[a-zA-Z0-9:]+@', "Database Connection String with password")
        ]

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                for pattern, msg in patterns:
                    if re.search(pattern, line):
                        issues.append({
                            "file": display_filename, "line": i + 1, "column": 0,
                            "rule": "UNIVERSAL-SECURITY", "severity": "critical",
                            "message": f"[SECURITY] {msg}", "line_text": line.strip(), "category": "security"
                        })
        
        return {"status": "success", "issues": issues}
    except:
        return {"status": "success", "issues": []}
