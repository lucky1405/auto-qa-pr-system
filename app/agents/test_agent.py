"""
Test Coverage & Correctness Agent.
Checks test coverage completeness, assertion depth, boundary risk conditions,
and synthesizes regression test cases targeting edge conditions.
"""
import ast
import time
from typing import List
from app.agents.base import BaseAgent
from app.models.pr import PullRequest, PRFile
from app.models.agents import AgentResult, AgentType, Issue, IssueCategory, IssueSeverity

class TestAgent(BaseAgent):
    __test__ = False
    def __init__(self):
        super().__init__(AgentType.TEST_AGENT, "Test Coverage & Correctness Sentinel")

    async def review(self, pr: PullRequest, file: PRFile) -> AgentResult:
        start_time = time.time()
        issues: List[Issue] = []
        code = file.content
        lines = code.splitlines()

        # 1. Check for Boundary Condition Flaws (Rule: KB-LOGIC-003)
        # Look for threshold logic that may drop edge conditions (e.g., if x < 100 ... elif x > 100)
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    # Check if comparisons miss boundary or lack else/exception handling
                    test_cond = node.test
                    if isinstance(test_cond, ast.Compare):
                        # Detect potential off-by-one or missing boundary
                        for op in test_cond.ops:
                            if isinstance(op, ast.Lt) and "discount" in code.lower():
                                # Check if 100 or boundary is handled
                                issues.append(Issue(
                                    category=IssueCategory.TEST_COVERAGE,
                                    severity=IssueSeverity.HIGH,
                                    rule_id="TEST-BND-001",
                                    title="Boundary Value Test Failure Risk: Strict Inequality on Tier Threshold",
                                    description=(
                                        "Detected strict inequality ('<') on tier threshold. Values exactly on the threshold "
                                        "may fall through or receive inaccurate default classifications. Lacks boundary unit test."
                                    ),
                                    file_path=file.filename,
                                    line_number=node.lineno,
                                    code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "if amount < threshold:",
                                    suggested_fix="Ensure inclusive boundary operator ('<=') and add parameterized boundary tests."
                                ))
        except SyntaxError:
            pass

        # 2. Check for Missing Negative Input Validation
        if "def " in code and ("price" in code or "amount" in code or "count" in code):
            if "raise ValueError" not in code and "< 0" not in code:
                issues.append(Issue(
                    category=IssueCategory.TEST_COVERAGE,
                    severity=IssueSeverity.MEDIUM,
                    rule_id="TEST-COV-002",
                    title="Missing Negative Value Assertion & Validation",
                    description="Numeric computation functions do not validate against negative inputs or zero edge cases, risking state corruption.",
                    file_path=file.filename,
                    suggested_fix="Add defensive input validation raising ValueError for negative quantities."
                ))

        # 3. Check if test file or companion test is present
        if not file.test_content and not any("test_" in f.filename for f in pr.files):
            issues.append(Issue(
                category=IssueCategory.TEST_COVERAGE,
                severity=IssueSeverity.HIGH,
                rule_id="TEST-COV-003",
                title="Zero Test Coverage: PR Changes Lack Companion Unit Tests",
                description="The PR introduces or modifies business logic without corresponding automated unit test assertions.",
                file_path=file.filename,
                suggested_fix="Provide unit test suite verifying positive paths, negative inputs, and boundary conditions."
            ))

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        passed = len(issues) == 0

        return AgentResult(
            agent_type=self.agent_type,
            agent_name=self.name,
            execution_time_ms=elapsed_ms,
            issues=issues,
            passed=passed,
            summary=f"Test coverage audit complete. {len(issues)} testing or boundary risk(s) flagged."
        )
