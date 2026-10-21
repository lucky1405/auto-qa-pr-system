"""
Tests for Sandbox Execution Runner.
"""
import pytest
from app.sandbox.isolated_runner import IsolatedSubprocessRunner

@pytest.mark.asyncio
async def test_sandbox_executes_passing_code():
    runner = IsolatedSubprocessRunner()
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    test_code = """
from module import add
def test_add():
    assert add(2, 3) == 5
"""
    result = await runner.execute(code, test_code, filename="module.py")
    assert result.success is True
    assert result.exit_code == 0
    assert result.tests_passed == 1
    assert result.tests_failed == 0

@pytest.mark.asyncio
async def test_sandbox_catches_failing_test():
    runner = IsolatedSubprocessRunner()
    code = """
def multiply(a, b):
    return a + b  # Defect: wrong operator
"""
    test_code = """
from module import multiply
def test_multiply():
    assert multiply(2, 3) == 6
"""
    result = await runner.execute(code, test_code, filename="module.py")
    assert result.success is False
    assert result.exit_code != 0
    assert result.tests_failed >= 1

@pytest.mark.asyncio
async def test_sandbox_catches_ast_security_violation():
    runner = IsolatedSubprocessRunner()
    code = """
def bad_query(cursor, name):
    cursor.execute(f"SELECT * FROM items WHERE name = '{name}'")
"""
    test_code = "def test_noop(): assert True"
    result = await runner.execute(code, test_code, filename="module.py")
    assert result.security_clean is False
    assert "Raw formatted string (f-string) detected" in result.security_output
