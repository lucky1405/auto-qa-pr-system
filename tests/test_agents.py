"""
Tests for Quality, Security, and Test Agents.
"""
import pytest
from app.models.pr import PullRequest, PRFile
from app.agents.quality_agent import QualityAgent
from app.agents.security_agent import SecurityAgent
from app.agents.test_agent import TestAgent
from app.models.agents import IssueSeverity

@pytest.mark.asyncio
async def test_security_agent_detects_sql_injection():
    agent = SecurityAgent()
    vulnerable_code = """
def query_user(cursor, email):
    cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
"""
    pr_file = PRFile(filename="query.py", content=vulnerable_code)
    pr = PullRequest(title="Test PR", files=[pr_file])

    result = await agent.review(pr, pr_file)
    assert not result.passed
    assert len(result.issues) > 0
    sql_issues = [i for i in result.issues if "SQL" in i.rule_id]
    assert len(sql_issues) == 1
    assert sql_issues[0].severity == IssueSeverity.CRITICAL
    assert sql_issues[0].cwe_id == "CWE-89"

@pytest.mark.asyncio
async def test_quality_agent_detects_unclosed_file():
    agent = QualityAgent()
    leak_code = """
def write_log(filepath, data):
    f = open(filepath, 'w')
    f.write(data)
    f.close()
"""
    pr_file = PRFile(filename="logger.py", content=leak_code)
    pr = PullRequest(title="Test PR", files=[pr_file])

    result = await agent.review(pr, pr_file)
    assert not result.passed
    assert any("RES" in i.rule_id for i in result.issues)

@pytest.mark.asyncio
async def test_clean_code_passes_agents():
    sec_agent = SecurityAgent()
    qual_agent = QualityAgent()

    clean_code = '''"""Token utility module."""
def verify_token(cursor, user_id: int) -> bool:
    """Verifies token securely using parameterized query."""
    cursor.execute("SELECT id FROM tokens WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None
'''
    pr_file = PRFile(filename="clean.py", content=clean_code)
    pr = PullRequest(title="Clean PR", files=[pr_file])

    sec_res = await sec_agent.review(pr, pr_file)
    qual_res = await qual_agent.review(pr, pr_file)

    assert sec_res.passed
    assert qual_res.passed
