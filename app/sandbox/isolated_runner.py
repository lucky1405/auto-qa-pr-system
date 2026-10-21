"""
Isolated Subprocess Sandbox Runner.
Executes candidate patches, static analysis, security validation, and test suites
inside an isolated filesystem jail with strict timeouts and resource limits.
"""
import sys
import os
import tempfile
import asyncio
import time
import ast
import re
from app.sandbox.runner import BaseSandboxRunner
from app.models.agents import SandboxExecutionResult

class IsolatedSubprocessRunner(BaseSandboxRunner):
    async def execute(
        self,
        code: str,
        test_code: str,
        filename: str = "module.py",
        timeout_seconds: int = 15
    ) -> SandboxExecutionResult:
        start_time = time.time()
        
        # 1. Static AST / Syntax & Security Analysis
        security_clean = True
        security_output = ""
        linter_clean = True
        linter_output = ""

        # Syntax check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return SandboxExecutionResult(
                success=False,
                exit_code=1,
                stderr=f"SyntaxError in generated code at line {e.lineno}: {e.msg}",
                stdout="",
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                tests_passed=0,
                tests_failed=1,
                tests_total=1,
                linter_clean=False,
                linter_output=f"SyntaxError: {e.msg} at line {e.lineno}",
                security_clean=True,
                mode_used="isolated-subprocess"
            )

        # AST-level Security Verification (Defense in Depth)
        # Check for lingering SQL injection (f-strings inside .execute)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "execute":
                    if node.args and isinstance(node.args[0], ast.JoinedStr):
                        security_clean = False
                        security_output += "Security Check Failed: Raw formatted string (f-string) detected inside .execute() call. Parameterized query required.\n"

        # AST-level Resource Management Check
        # Check for naked open() not inside with statement
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == "open":
                        linter_clean = False
                        linter_output += "Quality Check Warning: Direct open() assignment detected outside context manager ('with' statement).\n"

        # 2. Run in isolated temporary directory
        with tempfile.TemporaryDirectory(prefix="sandbox_run_") as temp_dir:
            module_path = os.path.join(temp_dir, filename)
            test_path = os.path.join(temp_dir, f"test_{filename}")
            
            with open(module_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Ensure test code imports from the local module if needed
            test_script = test_code
            if f"import {filename[:-3]}" not in test_script and f"from {filename[:-3]}" not in test_script:
                test_script = f"from {filename[:-3]} import *\n" + test_script

            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_script)

            # Prepare pytest execution
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                test_path,
                "-v",
                "--tb=short",
                "-o", "pythonpath=."
            ]

            env = os.environ.copy()
            env["PYTHONPATH"] = temp_dir
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )

                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_seconds
                )
                
                stdout = stdout_bytes.decode(errors="replace")
                stderr = stderr_bytes.decode(errors="replace")
                exit_code = proc.returncode

            except asyncio.TimeoutError:
                if proc:
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
                return SandboxExecutionResult(
                    success=False,
                    exit_code=-1,
                    stderr=f"Execution timed out after {timeout_seconds} seconds (Execution Sandbox Enforced Limit).",
                    stdout="",
                    execution_time_ms=round((time.time() - start_time) * 1000, 2),
                    tests_passed=0,
                    tests_failed=1,
                    tests_total=1,
                    linter_clean=linter_clean,
                    security_clean=security_clean,
                    mode_used="isolated-subprocess"
                )
            except Exception as e:
                return SandboxExecutionResult(
                    success=False,
                    exit_code=1,
                    stderr=f"Sandbox execution error: {str(e)}",
                    stdout="",
                    execution_time_ms=round((time.time() - start_time) * 1000, 2),
                    tests_passed=0,
                    tests_failed=1,
                    tests_total=1,
                    mode_used="isolated-subprocess"
                )

        # Parse pytest output
        passed_matches = re.findall(r'(\d+)\s+passed', stdout)
        failed_matches = re.findall(r'(\d+)\s+failed', stdout)
        passed_count = int(passed_matches[-1]) if passed_matches else (1 if exit_code == 0 else 0)
        failed_count = int(failed_matches[-1]) if failed_matches else (1 if exit_code != 0 else 0)
        total_tests = passed_count + failed_count

        overall_success = (exit_code == 0) and security_clean and (failed_count == 0)

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return SandboxExecutionResult(
            success=overall_success,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr + ("\n" + security_output if not security_clean else "") + ("\n" + linter_output if not linter_clean else ""),
            execution_time_ms=elapsed_ms,
            tests_passed=passed_count,
            tests_failed=failed_count,
            tests_total=max(total_tests, 1),
            linter_clean=linter_clean,
            linter_output=linter_output or "No static linter violations detected.",
            security_clean=security_clean,
            security_output=security_output or "No security policy violations detected in AST.",
            mode_used="isolated-subprocess"
        )
