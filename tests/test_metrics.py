"""
Tests for Software Quality, Complexity, and Reliability Metrics.
"""
import pytest
from app.metrics.code_metrics import CodeComplexityAnalyzer
from app.metrics.reliability import ReliabilityCalculator
from app.models.agents import Issue, IssueCategory, IssueSeverity

def test_code_complexity_analyzer():
    code = """
def process_data(items, flag):
    result = []
    if flag:
        for x in items:
            if x > 10:
                result.append(x * 2)
            else:
                result.append(x)
    return result
"""
    metrics = CodeComplexityAnalyzer.analyze(code)
    assert metrics.loc > 5
    assert metrics.cyclomatic_complexity >= 4
    assert 0 <= metrics.maintainability_index <= 100
    assert metrics.halstead_volume > 0

def test_reliability_calculator():
    issues = [
        Issue(
            category=IssueCategory.SECURITY,
            severity=IssueSeverity.CRITICAL,
            rule_id="SEC-001",
            title="SQLi",
            description="",
            file_path="mod.py"
        )
    ]

    rel = ReliabilityCalculator.calculate_reliability(
        loc=50,
        issues=issues,
        tests_passed=5,
        tests_total=5,
        repaired_issues_count=1
    )

    # 1 critical issue penalty = 25 -> base SRI = 75
    assert rel.software_reliability_index == 75.0
    assert rel.defect_density_per_kloc == 20.0 # 1 / 0.05 KLOC = 20
    assert rel.defect_removal_efficiency_pct == 100.0

def test_detection_accuracy_metrics():
    acc = ReliabilityCalculator.calculate_accuracy(
        true_positives=10,
        false_positives=0,
        false_negatives=0,
        true_negatives=50
    )

    assert acc.recall_defect_detection_rate == 1.0 # 100%
    assert acc.false_positive_rate == 0.0
    assert acc.precision == 1.0
    assert acc.f1_score == 1.0
