"""classifier — S3 failure classifier runtime (T3 CLASSIFIER.md implementation).

Детерминистический pattern-matcher: failure_observations → failure_class →
recovery_policy + evidence. Загружает failure_taxonomy.yaml.
"""
from .classifier import FailureClassifier, Classification, Evidence

__all__ = ["FailureClassifier", "Classification", "Evidence"]
