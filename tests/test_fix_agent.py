"""
Tests for Fix Agent (Automated Software Repair).
"""
import pytest
from app.agents.fix_agent import FixAgent
from app.models.agents import Issue, IssueCategory, IssueSeverity

def test_fix_agent_fixes_sql_injection():
    agent = FixAgent()
    orig = 'cursor.execute(f"SELECT * FROM users WHERE email = \'{email}\'")'
    issue = Issue(
        category=IssueCategory.SECURITY,
        severity=IssueSeverity.CRITICAL,
        rule_id="SEC-SQL-001",
        title="CWE-89: SQL Injection",
        description="f-string SQL query",
        file_path="auth.py",
        cwe_id="CWE-89"
    )

    patch = agent.generate_patch(
        file_path="auth.py",
        original_code=orig,
        issues=[issue],
        rag_rules=[{"id": "KB-SEC-001", "title": "SQL Injection Prevention"}]
    )

    assert "?" in patch.patched_code
    assert "email," in patch.patched_code
    assert "+" in patch.unified_diff
    assert "-" in patch.unified_diff
    assert "CWE-89" in patch.explanation

def test_fix_agent_fixes_boundary_logic():
    agent = FixAgent()
    orig = "if amount < 100:\n    return 0.05"
    issue = Issue(
        category=IssueCategory.TEST_COVERAGE,
        severity=IssueSeverity.HIGH,
        rule_id="TEST-BND-001",
        title="Boundary Value Test Failure Risk",
        description="Strict inequality",
        file_path="pricing.py"
    )

    patch = agent.generate_patch(
        file_path="pricing.py",
        original_code=orig,
        issues=[issue],
        rag_rules=[{"id": "KB-LOGIC-003", "title": "Boundary Safety"}]
    )

    assert "<= 100" in patch.patched_code
