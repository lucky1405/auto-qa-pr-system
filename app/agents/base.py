"""
Base Agent Interface for Multi-Agent PR Review Swarm.
"""
from abc import ABC, abstractmethod
import time
from app.models.pr import PullRequest, PRFile
from app.models.agents import AgentResult, AgentType

class BaseAgent(ABC):
    def __init__(self, agent_type: AgentType, name: str):
        self.agent_type = agent_type
        self.name = name

    @abstractmethod
    async def review(self, pr: PullRequest, file: PRFile) -> AgentResult:
        """
        Analyzes the given PR file and returns detected issues, metrics, and summary.
        """
        pass
