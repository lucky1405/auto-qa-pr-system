"""
Data models for Software Quality, Reliability, and Verification Metrics.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import datetime

class CodeComplexityMetrics(BaseModel):
    loc: int = 0
    sloc: int = 0
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 1
    maintainability_index: float = 100.0  # 0 to 100 scale (SEI standard)
    halstead_volume: float = 0.0
    halstead_difficulty: float = 0.0

class ReliabilityMetrics(BaseModel):
    defect_density_per_kloc: float = 0.0
    software_reliability_index: float = 100.0  # 0 to 100 scale
    estimated_failure_rate_lambda: float = 0.0  # Failures per 1000 hours
    projected_mtbf_hours: float = 10000.0       # Mean Time Between Failures
    defect_removal_efficiency_pct: float = 100.0 # DRE
    regression_risk_score: float = 0.0          # 0 to 10 scale

class DetectionAccuracyMetrics(BaseModel):
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    precision: float = 1.0
    recall_defect_detection_rate: float = 1.0
    false_positive_rate: float = 0.0
    f1_score: float = 1.0

class RepairMetrics(BaseModel):
    auto_fix_success_rate: float = 1.0
    first_pass_fix_rate: float = 1.0
    retry_recovery_rate: float = 0.0
    mean_time_to_repair_ms: float = 0.0
    total_repair_attempts: int = 0
    successful_repairs: int = 0

class RAGQualityMetrics(BaseModel):
    context_relevance_score: float = 1.0   # 0.0 to 1.0
    retrieval_precision: float = 1.0
    retrieval_recall: float = 1.0
    groundedness_faithfulness_score: float = 1.0
    hallucination_rate: float = 0.0

class ComprehensiveQualityReport(BaseModel):
    pr_id: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    pre_patch_complexity: CodeComplexityMetrics
    post_patch_complexity: CodeComplexityMetrics
    reliability: ReliabilityMetrics
    accuracy: DetectionAccuracyMetrics
    repair: RepairMetrics
    rag: RAGQualityMetrics
    test_coverage_pct: float = 0.0
    test_coverage_delta: float = 0.0
    overall_quality_grade: str = "A" # A+, A, B, C, D, F
    grade_explanation: str = ""
    formulas_and_explanations: Dict[str, str] = Field(default_factory=dict)
