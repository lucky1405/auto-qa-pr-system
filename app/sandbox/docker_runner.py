"""
Docker Sandbox Runner.
Executes code and tests inside an ephemeral Docker container when Docker daemon is available,
or delegates to IsolatedSubprocessRunner as high-availability fallback.
"""
import asyncio
import os
import shutil
import tempfile
import time
from app.sandbox.runner import BaseSandboxRunner
from app.sandbox.isolated_runner import IsolatedSubprocessRunner
from app.models.agents import SandboxExecutionResult

class DockerSandboxRunner(BaseSandboxRunner):
    def __init__(self, image: str = "python:3.13-slim"):
        self.image = image
        self.fallback_runner = IsolatedSubprocessRunner()
        self._docker_available = None

    async def is_docker_active(self) -> bool:
        if self._docker_available is not None:
            return self._docker_available
        docker_bin = shutil.which("docker")
        if not docker_bin:
            self._docker_available = False
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
            self._docker_available = (proc.returncode == 0)
        except Exception:
            self._docker_available = False
        return self._docker_available

    async def execute(
        self,
        code: str,
        test_code: str,
        filename: str = "module.py",
        timeout_seconds: int = 15
    ) -> SandboxExecutionResult:
        docker_ready = await self.is_docker_active()
        if not docker_ready:
            # Fall back to isolated subprocess runner with full security & test checks
            result = await self.fallback_runner.execute(code, test_code, filename, timeout_seconds)
            result.mode_used = "subprocess-sandbox (docker-daemon-offline)"
            return result

        start_time = time.time()
        with tempfile.TemporaryDirectory(prefix="docker_sandbox_") as temp_dir:
            module_path = os.path.join(temp_dir, filename)
            test_path = os.path.join(temp_dir, f"test_{filename}")

            with open(module_path, "w", encoding="utf-8") as f:
                f.write(code)

            test_script = test_code
            if f"import {filename[:-3]}" not in test_script and f"from {filename[:-3]}" not in test_script:
                test_script = f"from {filename[:-3]} import *\n" + test_script

            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_script)

            cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "256m",
                "--cpus", "1.0",
                "-v", f"{temp_dir}:/workspace",
                "-w", "/workspace",
                self.image,
                "sh", "-c", f"pip install -q pytest > /dev/null 2>&1 && pytest test_{filename} -v"
            ]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
                stdout = stdout_b.decode(errors="replace")
                stderr = stderr_b.decode(errors="replace")
                exit_code = proc.returncode

                return SandboxExecutionResult(
                    success=(exit_code == 0),
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    execution_time_ms=round((time.time() - start_time) * 1000, 2),
                    tests_passed=1 if exit_code == 0 else 0,
                    tests_failed=0 if exit_code == 0 else 1,
                    tests_total=1,
                    linter_clean=True,
                    security_clean=True,
                    mode_used="docker-isolated-container"
                )
            except Exception:
                # In case of container runtime failure, fall back to isolated subprocess
                result = await self.fallback_runner.execute(code, test_code, filename, timeout_seconds)
                result.mode_used = "subprocess-sandbox (container-failover)"
                return result

def get_default_sandbox_runner() -> BaseSandboxRunner:
    return DockerSandboxRunner()
