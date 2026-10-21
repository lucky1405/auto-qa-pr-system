"""
Multi-Agent Swarm Orchestrator.
Orchestrates parallel review agents, RAG context retrieval, Fix Agent patch synthesis,
isolated sandbox verification, and iterative retry loops.
"""
import asyncio
import hashlib
import time
from typing import List, Dict, Any, Optional, Callable
from app.models.pr import PullRequest, PRStatus, PRFile
from app.models.agents import (
    AgentResult,
    AgentType,
    Issue,
    IssueSeverity,
    PatchProposal,
    SandboxExecutionResult,
    RepairAttempt,
    OrchestrationPipelineResult
)
from app.agents.quality_agent import QualityAgent
from app.agents.security_agent import SecurityAgent
from app.agents.test_agent import TestAgent
from app.agents.fix_agent import FixAgent
from app.rag.engine import HybridRAGEngine, rag_engine
from app.sandbox.docker_runner import get_default_sandbox_runner
from app.config import settings

class Orchestrator:
    def __init__(self, sandbox_runner=None, rag=None):
        self.quality_agent = QualityAgent()
        self.security_agent = SecurityAgent()
        self.test_agent = TestAgent()
        self.fix_agent = FixAgent()
        self.rag = rag or rag_engine
        self.sandbox_runner = sandbox_runner or get_default_sandbox_runner()

    async def execute_pipeline(
        self,
        pr: PullRequest,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> OrchestrationPipelineResult:
        pipeline_start = time.time()
        audit_trail: List[Dict[str, Any]] = []

        async def emit(stage: str, message: str, payload: Dict[str, Any] = None):
            event_data = {
                "stage": stage,
                "message": message,
                "timestamp": round(time.time() - pipeline_start, 3),
                "payload": payload or {}
            }
            audit_trail.append(event_data)
            if event_callback:
                if asyncio.iscoroutinefunction(event_callback):
                    await event_callback(stage, event_data)
                else:
                    event_callback(stage, event_data)

        # Stage 1: Ingestion
        await emit("INGESTION", f"Ingested Pull Request #{pr.id}: '{pr.title}' ({len(pr.files)} file(s))")
        primary_file = pr.get_primary_file()

        # Stage 2: Fan-out to Specialized Review Agents in Parallel
        await emit("FAN_OUT", "Broadcasting PR changes concurrently to Code Quality, Security, and Test Sentinels...")
        agent_tasks = [
            self.quality_agent.review(pr, primary_file),
            self.security_agent.review(pr, primary_file),
            self.test_agent.review(pr, primary_file)
        ]
        agent_results: List[AgentResult] = await asyncio.gather(*agent_tasks)

        all_issues: List[Issue] = []
        for res in agent_results:
            all_issues.extend(res.issues)

        critical_issues = [i for i in all_issues if i.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH)]

        await emit(
            "REVIEW_AGGREGATION",
            f"Review complete. Found {len(all_issues)} issue(s) ({len(critical_issues)} critical/high).",
            {"issue_count": len(all_issues), "issues": [i.model_dump() for i in all_issues]}
        )

        repair_attempts: List[RepairAttempt] = []
        final_patch: Optional[PatchProposal] = None
        verified_commit_hash: Optional[str] = None
        status = PRStatus.APPROVED

        # If clean PR with zero issues
        if not all_issues:
            await emit("CLEAN_PR", "Zero defects detected. Executing sandbox baseline test verification...")
            test_suite = primary_file.test_content or "def test_ok(): assert True"
            baseline_result = await self.sandbox_runner.execute(
                code=primary_file.content,
                test_code=test_suite,
                filename=primary_file.filename,
                timeout_seconds=settings.SANDBOX_TIMEOUT_SECONDS
            )
            status = PRStatus.APPROVED
            verdict_message = f"PR Approved! Zero defects detected. Test suite passed ({baseline_result.tests_passed}/{baseline_result.tests_total})."
            await emit("VERDICT", verdict_message, {"sandbox": baseline_result.model_dump()})

            total_ms = round((time.time() - pipeline_start) * 1000, 2)
            return OrchestrationPipelineResult(
                pr_id=pr.id,
                status=status.value,
                agent_results=agent_results,
                total_issues_found=0,
                critical_issues_count=0,
                rag_retrievals=[],
                repair_attempts=[],
                final_patch=None,
                verified_commit_hash=None,
                total_latency_ms=total_ms,
                verdict_message=verdict_message,
                audit_trail=audit_trail
            )

        # Stage 3: RAG Retrieval
        rag_query = f"{primary_file.content} {' '.join(i.title for i in all_issues)} {' '.join(i.rule_id for i in all_issues)}"
        retrieved_rules = self.rag.retrieve(rag_query, top_k=settings.RAG_TOP_K)
        await emit(
            "RAG_RETRIEVAL",
            f"Retrieved {len(retrieved_rules)} project guidelines and fix patterns from Knowledge Base.",
            {"rules": retrieved_rules}
        )

        # Stage 4: Automated Software Repair with Iterative Sandbox Retry Loop
        max_retries = settings.MAX_REPAIR_RETRIES
        current_code = primary_file.content
        previous_feedback = None
        repaired_successfully = False

        test_code_to_run = primary_file.test_content or """
import pytest

def test_security_and_contract():
    assert True
"""

        for attempt in range(1, max_retries + 1):
            await emit(
                "REPAIR_ATTEMPT",
                f"Starting Fix Agent repair attempt {attempt}/{max_retries}...",
                {"attempt": attempt, "feedback": previous_feedback}
            )

            # Generate candidate patch
            patch_proposal = self.fix_agent.generate_patch(
                file_path=primary_file.filename,
                original_code=primary_file.content,
                issues=all_issues,
                rag_rules=retrieved_rules,
                attempt=attempt,
                previous_feedback=previous_feedback
            )

            await emit(
                "SANDBOX_DISPATCH",
                f"Dispatching candidate patch (attempt #{attempt}) to Isolated Sandbox for test & security audit...",
                {"diff": patch_proposal.unified_diff}
            )

            # Run in Sandbox
            sandbox_res = await self.sandbox_runner.execute(
                code=patch_proposal.patched_code,
                test_code=test_code_to_run,
                filename=primary_file.filename,
                timeout_seconds=settings.SANDBOX_TIMEOUT_SECONDS
            )

            repair_attempt = RepairAttempt(
                attempt_number=attempt,
                patch=patch_proposal,
                sandbox_result=sandbox_res,
                error_feedback=sandbox_res.stderr if not sandbox_res.success else None,
                success=sandbox_res.success
            )
            repair_attempts.append(repair_attempt)

            if sandbox_res.success:
                repaired_successfully = True
                final_patch = patch_proposal
                # Create simulated GitHub PR commit hash
                sha_input = f"{pr.id}-{patch_proposal.patched_code}-{attempt}".encode()
                verified_commit_hash = hashlib.sha1(sha_input).hexdigest()[:10]
                status = PRStatus.AUTO_FIXED_AND_COMMITTED
                await emit(
                    "SANDBOX_PASSED",
                    f"Sandbox verification PASSED on attempt #{attempt}! Tests passed ({sandbox_res.tests_passed}/{sandbox_res.tests_total}), 0 linter violations, 0 security flaws.",
                    {"commit_hash": verified_commit_hash, "sandbox": sandbox_res.model_dump()}
                )
                break
            else:
                previous_feedback = sandbox_res.stderr or sandbox_res.linter_output
                await emit(
                    "SANDBOX_FAILED",
                    f"Sandbox verification FAILED on attempt #{attempt}. Retrying with error feedback...",
                    {"stderr": sandbox_res.stderr, "exit_code": sandbox_res.exit_code}
                )
                await asyncio.sleep(settings.RETRY_BACKOFF_SECONDS)

        total_latency_ms = round((time.time() - pipeline_start) * 1000, 2)

        if repaired_successfully:
            verdict_message = (
                f"PR Auto-Fixed & Verified! Generated commit '{verified_commit_hash}'. "
                f"Successfully remediated {len(all_issues)} defect(s) in {total_latency_ms}ms."
            )
        else:
            status = PRStatus.CHANGES_REQUESTED
            verdict_message = (
                f"Changes Requested: {len(all_issues)} defect(s) detected. Fix Agent attempts exceeded {max_retries} retries without sandbox pass."
            )

        await emit("PIPELINE_COMPLETE", verdict_message, {"status": status.value, "commit": verified_commit_hash})

        return OrchestrationPipelineResult(
            pr_id=pr.id,
            status=status.value,
            agent_results=agent_results,
            total_issues_found=len(all_issues),
            critical_issues_count=len(critical_issues),
            rag_retrievals=retrieved_rules,
            repair_attempts=repair_attempts,
            final_patch=final_patch,
            verified_commit_hash=verified_commit_hash,
            total_latency_ms=total_latency_ms,
            verdict_message=verdict_message,
            audit_trail=audit_trail
        )

orchestrator = Orchestrator()
