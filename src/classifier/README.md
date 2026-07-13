# `src/classifier/` — S3 failure classifier runtime (T3)

> Детерминистический pattern-matcher: failure_observations → failure_class →
> recovery_policy + evidence. Загружает failure_taxonomy.yaml. Не использует LLM.

## Modules

- `types.py` — TaxonomyClass, Evidence, Classification dataclasses.
- `taxonomy_loader.py` — loads/parses failure_taxonomy.yaml.
- `classifier.py` — FailureClassifier: classify(observations) → Classification.

## Usage

```python
import sys; sys.path.insert(0, 'src')
from classifier.classifier import FailureClassifier

clf = FailureClassifier("src/failure_taxonomy.yaml")

observations = [
    {"kind": "error_string", "value": "ModuleNotFoundError: No module named 'pytest'", "source": "stderr", "at_action": 3},
    {"kind": "exit_code", "value": 1, "command": "pytest tests/", "at_action": 3},
]

result = clf.classify(observations)
print(result.failure_class)      # ImportError
print(result.recovery_policy)    # InstallDependency
print(result.confidence)         # high
print(result.evidence)           # [Evidence(signal='ModuleNotFoundError', ...)]
```

## Classification pipeline (CLASSIFIER.md §2-3)

1. For each observation, match against all class signals (substring + regex).
2. Rank matched classes by match_order (code→dependency→git→...→fallback).
3. Multi-match: prefer class with more evidence; same count → ambiguous.
4. No matches → Unknown → EscalateToS3.
5. Evidence required: every decision has matched signal string.

## General-purpose

Classifier не привязан к конкретному оценочному набору. Signals — universal
error strings (ModuleNotFoundError, SyntaxError, ConnectionError, ...).
