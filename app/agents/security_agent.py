"""
Security & Vulnerability Agent.
Detects OWASP Top 10 vulnerabilities, CWE compliance violations, hardcoded credentials,
SQL injection vectors, and command injection flaws.
"""
import ast
import re
import time
from typing import List
from app.agents.base import BaseAgent
from app.models.pr import PullRequest, PRFile
from app.models.agents import AgentResult, AgentType, Issue, IssueCategory, IssueSeverity

class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.SECURITY_AGENT, "Security & Vulnerability Sentinel")

    async def review(self, pr: PullRequest, file: PRFile) -> AgentResult:
        start_time = time.time()
        issues: List[Issue] = []
        code = file.content
        lines = code.splitlines()

        # 1. AST Analysis for SQL Injection (CWE-89)
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # Detect .execute(...) with f-string or % or +
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Attribute) and func.attr == "execute":
                        if node.args:
                            first_arg = node.args[0]
                            # JoinedStr is an f-string in Python AST
                            if isinstance(first_arg, ast.JoinedStr):
                                issues.append(Issue(
                                    category=IssueCategory.SECURITY,
                                    severity=IssueSeverity.CRITICAL,
                                    rule_id="SEC-SQL-001",
                                    title="CWE-89: SQL Injection Vulnerability via Formatted String",
                                    description=(
                                        "Detected raw user inputs formatted directly into a SQL query string using f-string. "
                                        "An attacker can manipulate the query structure to bypass authentication or extract sensitive database tables."
                                    ),
                                    file_path=file.filename,
                                    line_number=node.lineno,
                                    code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "cursor.execute(f'...)",
                                    suggested_fix="Replace string interpolation with parameterized query syntax: cursor.execute('SELECT ... WHERE col = ?', (val,))",
                                    cwe_id="CWE-89",
                                    cvss_score=9.8
                                ))
                            elif isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, (ast.Add, ast.Mod)):
                                issues.append(Issue(
                                    category=IssueCategory.SECURITY,
                                    severity=IssueSeverity.CRITICAL,
                                    rule_id="SEC-SQL-001",
                                    title="CWE-89: SQL Injection Vulnerability via String Concatenation",
                                    description="Detected dynamic SQL query construction using '+' or '%' string concatenation.",
                                    file_path=file.filename,
                                    line_number=node.lineno,
                                    code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "cursor.execute('...' + ...)",
                                    suggested_fix="Use parameterized queries with bound arguments.",
                                    cwe_id="CWE-89",
                                    cvss_score=9.8
                                ))

                # Detect Command Injection (CWE-78)
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Attribute) and func.attr in ("system", "popen"):
                        if isinstance(func.value, ast.Name) and func.value.id == "os":
                            issues.append(Issue(
                                category=IssueCategory.SECURITY,
                                severity=IssueSeverity.CRITICAL,
                                rule_id="SEC-CMD-002",
                                title="CWE-78: Potential OS Command Injection via os.system",
                                description="Direct invocation of system shell with dynamic arguments can lead to arbitrary code execution.",
                                file_path=file.filename,
                                line_number=node.lineno,
                                code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "os.system(...)",
                                suggested_fix="Use subprocess.run with explicit argument array and shell=False.",
                                cwe_id="CWE-78",
                                cvss_score=9.4
                            ))

                # Detect Unsafe Deserialization (CWE-502)
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Attribute) and func.attr == "loads":
                        if isinstance(func.value, ast.Name) and func.value.id == "pickle":
                            issues.append(Issue(
                                category=IssueCategory.SECURITY,
                                severity=IssueSeverity.HIGH,
                                rule_id="SEC-DESER-003",
                                title="CWE-502: Deserialization of Untrusted Data via Pickle",
                                description="Pickle deserialization of untrusted input allows arbitrary remote code execution via __reduce__.",
                                file_path=file.filename,
                                line_number=node.lineno,
                                suggested_fix="Use secure serialization formats like JSON, Protocol Buffers, or HMAC signing.",
                                cwe_id="CWE-502",
                                cvss_score=8.8
                            ))
        except SyntaxError:
            pass

        # 2. Regex Check for Hardcoded Secrets (CWE-798)
        secret_patterns = [
            (r'(?i)(api[_-]?key|secret[_-]?key|password|jwt[_-]?token)\s*=\s*["\']([a-zA-Z0-9_\-\.]{8,})["\']', "Hardcoded Secret / API Key Detected")
        ]
        for idx, line in enumerate(lines, 1):
            for pattern, msg in secret_patterns:
                # Exclude obvious mock words or env lookups
                if "os.getenv" in line or "os.environ" in line or "test_key" in line or "example" in line:
                    continue
                match = re.search(pattern, line)
                if match:
                    issues.append(Issue(
                        category=IssueCategory.SECURITY,
                        severity=IssueSeverity.HIGH,
                        rule_id="SEC-SEC-004",
                        title=f"CWE-798: {msg}",
                        description="Hardcoded credential identified in source code. Credentials must never be stored in version control.",
                        file_path=file.filename,
                        line_number=idx,
                        code_snippet=line.strip(),
                        suggested_fix="Extract secret into environment variable or secret manager (e.g. os.getenv('SECRET_KEY')).",
                        cwe_id="CWE-798",
                        cvss_score=7.5
                    ))

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        passed = len(issues) == 0

        return AgentResult(
            agent_type=self.agent_type,
            agent_name=self.name,
            execution_time_ms=elapsed_ms,
            issues=issues,
            passed=passed,
            summary=f"Security scan completed. {len(issues)} vulnerability/flaw(s) discovered."
        )
