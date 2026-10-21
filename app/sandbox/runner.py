"""
Base Sandbox Runner Interface.
"""
from abc import ABC, abstractmethod
from app.models.agents import SandboxExecutionResult

class BaseSandboxRunner(ABC):
    @abstractmethod
    async def execute(
        self,
        code: str,
        test_code: str,
        filename: str = "module.py",
        timeout_seconds: int = 15
    ) -> SandboxExecutionResult:
        """
        Executes code + tests + linting + security checks inside an isolated environment.
        """
        pass
