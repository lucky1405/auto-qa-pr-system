"""
Software Reliability and Quality Metric Calculators.
Implements IEEE and industry-standard reliability metrics: MTBF, Defect Density,
Software Reliability Index (SRI), Defect Removal Efficiency (DRE), and Accuracy.
"""
from typing import List, Dict, Any, Optional
from app.models.agents import Issue, IssueSeverity, RepairAttempt
from app.models.metrics import ReliabilityMetrics, DetectionAccuracyMetrics, RepairMetrics

class ReliabilityCalculator:
    @staticmethod
    def calculate_reliability(
        loc: int,
        issues: List[Issue],
        tests_passed: int,
        tests_total: int,
        repaired_issues_count: int
    ) -> ReliabilityMetrics:
        kloc = max(loc, 1) / 1000.0
        defect_density = len(issues) / kloc

        crit_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
        med_count = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)
        low_count = sum(1 for i in issues if i.severity == IssueSeverity.LOW)

        # Failure rate lambda (failures expected per 1000 hours of runtime)
        lambda_rate = (crit_count * 0.12) + (high_count * 0.05) + (med_count * 0.015) + (low_count * 0.002)

        # Projected Mean Time Between Failures (MTBF)
        # MTBF = 1 / lambda (in hours)
        mtbf_hours = 1.0 / max(lambda_rate, 0.0001)

        # Software Reliability Index (SRI) on a 0-100 scale
        # Accounts for defect severity penalties and unit test execution pass ratio
        penalty = (crit_count * 25.0) + (high_count * 15.0) + (med_count * 6.0) + (low_count * 2.0)
        base_sri = max(0.0, 100.0 - penalty)
        test_ratio = (tests_passed / max(tests_total, 1)) if tests_total > 0 else 1.0
        final_sri = base_sri * test_ratio

        # Defect Removal Efficiency (DRE) = Defects Fixed / Defects Discovered
        total_defects = len(issues)
        dre = (repaired_issues_count / total_defects * 100.0) if total_defects > 0 else 100.0

        # Regression Risk Score (0 to 10 scale)
        regression_risk = min(10.0, (crit_count * 3.5) + (high_count * 2.0) + (med_count * 0.8) + (1.0 - test_ratio) * 5.0)

        return ReliabilityMetrics(
            defect_density_per_kloc=round(defect_density, 2),
            software_reliability_index=round(final_sri, 2),
            estimated_failure_rate_lambda=round(lambda_rate, 4),
            projected_mtbf_hours=round(min(mtbf_hours, 50000.0), 1),
            defect_removal_efficiency_pct=round(dre, 2),
            regression_risk_score=round(regression_risk, 2)
        )

    @staticmethod
    def calculate_accuracy(
        true_positives: int,
        false_positives: int,
        false_negatives: int,
        true_negatives: int
    ) -> DetectionAccuracyMetrics:
        # Defect Detection Rate (Recall / Sensitivity) = TP / (TP + FN)
        recall = true_positives / max(true_positives + false_negatives, 1)
        # Precision = TP / (TP + FP)
        precision = true_positives / max(true_positives + false_positives, 1)
        # False Positive Rate = FP / (FP + TN)
        fpr = false_positives / max(false_positives + true_negatives, 1)
        # F1 Score
        f1 = (2 * precision * recall) / max(precision + recall, 0.0001)

        return DetectionAccuracyMetrics(
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            true_negatives=true_negatives,
            precision=round(precision, 3),
            recall_defect_detection_rate=round(recall, 3),
            false_positive_rate=round(fpr, 3),
            f1_score=round(f1, 3)
        )

    @staticmethod
    def calculate_repair_metrics(
        attempts: List[RepairAttempt],
        total_latency_ms: float
    ) -> RepairMetrics:
        if not attempts:
            return RepairMetrics(
                auto_fix_success_rate=1.0,
                first_pass_fix_rate=1.0,
                retry_recovery_rate=0.0,
                mean_time_to_repair_ms=0.0,
                total_repair_attempts=0,
                successful_repairs=0
            )

        total_attempts = len(attempts)
        successful_repairs = sum(1 for a in attempts if a.success)
        first_pass = 1 if (attempts and attempts[0].success) else 0
        retry_recovery = 1 if (successful_repairs > 0 and not (attempts and attempts[0].success)) else 0

        success_rate = successful_repairs / max(total_attempts, 1)
        mttr = total_latency_ms / max(successful_repairs, 1) if successful_repairs > 0 else total_latency_ms

        return RepairMetrics(
            auto_fix_success_rate=round(success_rate, 3),
            first_pass_fix_rate=round(first_pass / max(1, len(attempts)), 3),
            retry_recovery_rate=round(retry_recovery / max(1, len(attempts)), 3),
            mean_time_to_repair_ms=round(mttr, 2),
            total_repair_attempts=total_attempts,
            successful_repairs=successful_repairs
        )
