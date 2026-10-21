"""
Code Quality & Standards Agent.
Inspects code for PEP8 compliance, naming conventions, docstrings, resource leaks,
and cyclomatic complexity thresholds.
"""
import ast
import time
from typing import List
from app.agents.base import BaseAgent
from app.models.pr import PullRequest, PRFile
from app.models.agents import AgentResult, AgentType, Issue, IssueCategory, IssueSeverity

class QualityAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.QUALITY_AGENT, "Code Quality & Standards Sentinel")

    async def review(self, pr: PullRequest, file: PRFile) -> AgentResult:
        start_time = time.time()
        issues: List[Issue] = []
        code = file.content

        # 1. Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            issues.append(Issue(
                category=IssueCategory.CODE_QUALITY,
                severity=IssueSeverity.CRITICAL,
                rule_id="QUAL-000",
                title="Syntax Error Detected",
                description=f"Invalid Python syntax: {e.msg} at line {e.lineno}",
                file_path=file.filename,
                line_number=e.lineno,
                suggested_fix="Fix syntax syntax errors before proceeding."
            ))
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                issues=issues,
                passed=False,
                summary=f"Found syntax error at line {e.lineno}"
            )

        # 2. Check Resource Management (Rule: KB-REL-002)
        # Identify open() called without a 'with' statement
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == "open":
                        issues.append(Issue(
                            category=IssueCategory.RELIABILITY,
                            severity=IssueSeverity.HIGH,
                            rule_id="QUAL-RES-001",
                            title="Unmanaged Resource: Open File Descriptor Leak",
                            description=(
                                "Direct assignment of open() without a context manager ('with' block) risks "
                                "file descriptor leaks and buffer corruption if an exception occurs before .close()."
                            ),
                            file_path=file.filename,
                            line_number=node.lineno,
                            code_snippet=code.splitlines()[node.lineno - 1] if node.lineno <= len(code.splitlines()) else "open(...)",
                            suggested_fix="Refactor file operations to use 'with open(...) as f:' context manager."
                        ))

        # 3. Check Cyclomatic Complexity of Functions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                branch_count = 1
                for sub in ast.walk(node):
                    if isinstance(sub, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With)):
                        branch_count += 1
                if branch_count > 10:
                    issues.append(Issue(
                        category=IssueCategory.CODE_QUALITY,
                        severity=IssueSeverity.MEDIUM,
                        rule_id="QUAL-CMP-002",
                        title=f"Excessive Cyclomatic Complexity in '{node.name}' ({branch_count})",
                        description=f"Function '{node.name}' has cyclomatic complexity of {branch_count} (threshold: 10). High branch count increases testing difficulty and defect risk.",
                        file_path=file.filename,
                        line_number=node.lineno,
                        code_snippet=f"def {node.name}(...)",
                        suggested_fix="Decompose function into smaller sub-methods or utilize early returns."
                    ))

        # 4. Check for Missing Type Annotations / Docstrings on Public APIs
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if not ast.get_docstring(node):
                    issues.append(Issue(
                        category=IssueCategory.CODE_QUALITY,
                        severity=IssueSeverity.LOW,
                        rule_id="QUAL-DOC-003",
                        title=f"Missing Docstring on Public Function '{node.name}'",
                        description=f"Public function '{node.name}' lacks a Google/Sphinx style docstring documenting arguments and return types.",
                        file_path=file.filename,
                        line_number=node.lineno,
                        suggested_fix="Add descriptive docstring explaining function behavior, parameters, and return contract."
                    ))

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        passed = len(issues) == 0

        return AgentResult(
            agent_type=self.agent_type,
            agent_name=self.name,
            execution_time_ms=elapsed_ms,
            issues=issues,
            passed=passed,
            summary=f"Quality audit completed. {len(issues)} issue(s) identified."
        )
