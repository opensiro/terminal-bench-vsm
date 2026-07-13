# `src/audit/` — S3* independent audit runtime (VSM-005 §5)

> S3* independently audits S3-classifier decisions. Does NOT trust self-reports.
> Checks: classification consistency, signal coverage, structural defects,
> uncertainty-reaction viability. Cross-provider (config point).

## Modules

- `config.py` — AuditConfig: cross-provider constraint, thresholds, scope.
- `types.py` — AuditFinding, AuditResult, Severity, FindingType.
- `auditor.py` — S3StarAuditor: audit_classification(), audit_unknown_share().

## Cross-provider (VSM-001/VSM-005)

S3* MUST use a different model provider than S1. This is a config point:
```python
config = AuditConfig(
    s1_provider="openai",
    s3star_provider="anthropic",  # MUST differ
)
error = config.validate_provider_constraint()  # None if OK
```

## Usage

```python
import sys; sys.path.insert(0, 'src')
from audit.auditor import S3StarAuditor
from audit.config import AuditConfig

config = AuditConfig(s1_provider="openai", s3star_provider="anthropic")
auditor = S3StarAuditor(config)

result = auditor.audit_classification(
    classification={
        "failure_class": "ImportError",
        "recovery_policy": "InstallDependency",
        "confidence": "high",
        "evidence": [{"signal": "ModuleNotFoundError", "observation_value": "...", "observation_kind": "error_string", "at_action": 3}],
        "ambiguous": False,
    },
    observations=[
        {"kind": "error_string", "value": "ModuleNotFoundError: No module named pytest", "source": "stderr", "at_action": 3},
    ],
    taxonomy_classes=[...],  # from failure_taxonomy.yaml
)

print(result.passed)        # True if no critical findings
print(result.algedonic)     # True if should escalate to S5
print(len(result.findings)) # number of findings
```

## Audit checks (VSM-005 §5)

1. **Classification consistency**: evidence supports the class? signals found in observations?
2. **Signal coverage**: unmatched observations → taxonomy gap?
3. **Structural defects**: Unknown class, ambiguous classification, oscillation (A→B→A→B).
4. **Uncertainty reaction**: low confidence → S2 probing / S4 expansion needed?
5. **Provider constraint**: S3* provider ≠ S1 provider (critical invariant).

## Independence

S3* does NOT trust S3's self-reports. It re-verifies:
- That evidence signals actually appear in observations.
- That classification is consistent with signal coverage.
- That no oscillation pattern exists in recent history.

## Algedonic escalation

Critical findings → `result.algedonic = True` → S5 (architect) intervention.
