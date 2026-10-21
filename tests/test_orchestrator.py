"""
Tests for End-to-End Orchestrator Pipeline.
"""
import pytest
from app.models.pr import PullRequest, PRFile, PRStatus
from app.agents.orchestrator import orchestrator
from app.data.scenarios import SCENARIOS

@pytest.mark.asyncio
async def test_orchestrator_fixes_sql_injection():
    sc = next(s for s in SCENARIOS if s["id"] == "scenario-sql-injection")
    pr_file = PRFile(
        filename=sc["filename"],
        content=sc["content"],
        test_content=sc["test_content"]
    )
    pr = PullRequest(
        title=sc["title"],
        files=[pr_file]
    )

    result = await orchestrator.execute_pipeline(pr)

    assert result.status == PRStatus.AUTO_FIXED_AND_COMMITTED.value
    assert result.verified_commit_hash is not None
    assert result.final_patch is not None
    assert "?" in result.final_patch.patched_code
    assert len(result.repair_attempts) >= 1
    assert result.repair_attempts[0].success is True

@pytest.mark.asyncio
async def test_orchestrator_approves_clean_pr():
    sc = next(s for s in SCENARIOS if s["id"] == "scenario-clean-pr")
    pr_file = PRFile(
        filename=sc["filename"],
        content=sc["content"],
        test_content=sc["test_content"]
    )
    pr = PullRequest(
        title=sc["title"],
        files=[pr_file]
    )

    result = await orchestrator.execute_pipeline(pr)

    assert result.status == PRStatus.APPROVED.value
    assert result.total_issues_found == 0
    assert result.final_patch is None
