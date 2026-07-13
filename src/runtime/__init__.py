"""runtime — s1-dispatcher runtime (T2 CONTRACT implementation).

S1 stateless: fresh-per-invocation. Budget enforcement. Trace collection.
Failure observations extraction. Artifacts diff.
"""
from .dispatcher import S1Dispatcher, invoke
from .types import S1Input, S1Output, TraceEntry, FailureObservation, Verdict

__all__ = ["S1Dispatcher", "invoke", "S1Input", "S1Output", "TraceEntry", "FailureObservation", "Verdict"]
