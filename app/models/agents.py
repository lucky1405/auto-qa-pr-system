"""
Data models for Review Agents, Issues, Patches, and Sandbox Results.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
import datetime

class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class IssueCategory(str, Enum):
    SECURITY = "SECURITY"
    CODE_QUALITY = "CODE_QUALITY"
    TEST_COVERAGE = "TEST_COVERAGE"
    RELIABILITY = "RELIABILITY"
    PERFORMANCE = "PERFORMANCE"

class Issue(BaseModel):
    id: str = Field(default_factory=lambda: f"iss-{uuid.uuid4().hex[:6]}")
    category: IssueCategory
    severity: IssueSeverity
    rule_id: str
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None

class AgentType(str, Enum):
    ORCHESTRATOR = "ORCHESTRATOR"
    QUALITY_AGENT = "QUALITY_AGENT"
    SECURITY_AGENT = "SECURITY_AGENT"
    TEST_AGENT = "TEST_AGENT"
    FIX_AGENT = "FIX_AGENT"
    SANDBOX = "SANDBOX"

class AgentResult(BaseModel):
    agent_type: AgentType
    agent_name: str
    execution_time_ms: float
    issues: List[Issue] = Field(default_factory=list)
    passed: bool = True
    summary: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PatchProposal(BaseModel):
    id: str = Field(default_factory=lambda: f"patch-{uuid.uuid4().hex[:6]}")
    file_path: str
    original_code: str
    patched_code: str
    unified_diff: str
    explanation: str
    targeted_issue_ids: List[str] = Field(default_factory=list)
    rag_citations: List[str] = Field(default_factory=list)

class SandboxExecutionResult(BaseModel):
    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0
    linter_clean: bool = True
    linter_output: str = ""
    security_clean: bool = True
    security_output: str = ""
    mode_used: str = "subprocess-isolated"

class RepairAttempt(BaseModel):
    attempt_number: int
    patch: PatchProposal
    sandbox_result: SandboxExecutionResult
    error_feedback: Optional[str] = None
    success: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

class OrchestrationPipelineResult(BaseModel):
    pr_id: str
    status: str
    agent_results: List[AgentResult] = Field(default_factory=list)
    total_issues_found: int = 0
    critical_issues_count: int = 0
    rag_retrievals: List[Dict[str, Any]] = Field(default_factory=list)
    repair_attempts: List[RepairAttempt] = Field(default_factory=list)
    final_patch: Optional[PatchProposal] = None
    verified_commit_hash: Optional[str] = None
    total_latency_ms: float = 0.0
    verdict_message: str = ""
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)
