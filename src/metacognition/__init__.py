"""
Metacognition Engine for Protocol OMNI v14.0 SOVEREIGN GENESIS

Higher-order reasoning layer that monitors agent outputs for
confabulation and logical errors through a series of verification gates.
"""

from .engine import MetacognitionEngine, VerificationResult
from .gates import ConfidenceGate, EvidenceGate, SelfCheckGate, SymbolicGate

__all__ = [
    "MetacognitionEngine",
    "VerificationResult",
    "SelfCheckGate",
    "EvidenceGate",
    "ConfidenceGate",
    "SymbolicGate",
]
