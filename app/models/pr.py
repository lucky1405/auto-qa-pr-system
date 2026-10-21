"""
Data models for Pull Requests and Code Changes.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
import datetime

class PRStatus(str, Enum):
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    ISSUES_FOUND = "ISSUES_FOUND"
    CLEAN = "CLEAN"
    REPAIRING = "REPAIRING"
    VERIFYING = "VERIFYING"
    RETRYING = "RETRYING"
    AUTO_FIXED_AND_COMMITTED = "AUTO_FIXED_AND_COMMITTED"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    FAILED = "FAILED"

class PRFile(BaseModel):
    filename: str
    content: str
    original_content: Optional[str] = None
    diff: Optional[str] = None
    test_content: Optional[str] = None
    language: str = "python"
    additions: int = 0
    deletions: int = 0

class PullRequest(BaseModel):
    id: str = Field(default_factory=lambda: f"pr-{uuid.uuid4().hex[:8]}")
    title: str
    description: str = ""
    repo: str = "acme-corp/core-service"
    branch: str = "feature/api-v2"
    base_branch: str = "main"
    author: str = "alex_developer"
    files: List[PRFile]
    status: PRStatus = PRStatus.QUEUED
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_primary_file(self) -> PRFile:
        return self.files[0] if self.files else PRFile(filename="unknown.py", content="")
