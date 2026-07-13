"""audit — S3* independent audit runtime (VSM-005 §5).

S3* independently audits S3-classifier decisions: consistency, signal coverage,
structural defects, uncertainty-reaction viability. Cross-provider (config point).
"""
from .auditor import S3StarAuditor, AuditResult, AuditFinding
from .config import AuditConfig

__all__ = ["S3StarAuditor", "AuditResult", "AuditFinding", "AuditConfig"]
