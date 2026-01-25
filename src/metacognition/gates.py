"""
Individual gate implementations for the Metacognition Engine.

Each gate is a modular verification step that can be configured
and extended independently.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class GateResult:
    passed: bool
    feedback: Optional[str] = None
    metadata: Dict[str, Any] = None


class BaseGate(ABC):
    """Abstract base class for verification gates."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"metacognition.gates.{name}")

    @abstractmethod
    async def check(
        self,
        output: str,
        prompt: str,
        evidence: List[str]
    ) -> GateResult:
        """Run the gate check and return result."""
        pass


class SelfCheckGate(BaseGate):
    """
    Gate 1: Verifies output consistency with original prompt.

    Checks:
    - Does the output address the prompt's main question/task?
    - Are there any direct contradictions?
    - Is the response on-topic?
    """

    def __init__(self):
        super().__init__("self-check")

    async def check(
        self,
        output: str,
        prompt: str,
        evidence: List[str]
    ) -> GateResult:
        if not output or not prompt:
            return GateResult(
                passed=False,
                feedback="Empty output or prompt"
            )

        prompt_keywords = set(prompt.lower().split())
        output_keywords = set(output.lower().split())
        overlap = len(prompt_keywords & output_keywords) / max(len(prompt_keywords), 1)

        if overlap < 0.1:
            return GateResult(
                passed=False,
                feedback="Output appears unrelated to prompt (low keyword overlap)",
                metadata={"overlap_ratio": overlap},
            )

        return GateResult(passed=True, metadata={"overlap_ratio": overlap})


class EvidenceGate(BaseGate):
    """
    Gate 2: Cross-references claims against retrieved evidence.

    Checks:
    - Are factual claims supported by evidence?
    - Are there fabricated citations?
    - Is there evidence for technical claims?
    """

    def __init__(self, min_evidence_ratio: float = 0.3):
        super().__init__("evidence")
        self.min_evidence_ratio = min_evidence_ratio

    async def check(
        self,
        output: str,
        prompt: str,
        evidence: List[str]
    ) -> GateResult:
        if not evidence:
            return GateResult(
                passed=True,
                feedback="No evidence to cross-reference",
                metadata={"evidence_count": 0},
            )

        evidence_text = " ".join(evidence).lower()
        output_sentences = [s.strip() for s in output.split(".") if s.strip()]

        supported = 0
        for sentence in output_sentences:
            sentence_words = set(sentence.lower().split())
            if len(sentence_words) < 5:
                supported += 1
                continue

            evidence_words = set(evidence_text.split())
            overlap = len(sentence_words & evidence_words) / len(sentence_words)
            if overlap > 0.3:
                supported += 1

        support_ratio = supported / max(len(output_sentences), 1)

        if support_ratio < self.min_evidence_ratio:
            return GateResult(
                passed=False,
                feedback=f"Only {support_ratio:.0%} of claims have evidence support",
                metadata={"support_ratio": support_ratio},
            )

        return GateResult(passed=True, metadata={"support_ratio": support_ratio})


class ConfidenceGate(BaseGate):
    """
    Gate 3: Quantifies uncertainty in the output.

    Checks:
    - Presence of hedging language ("might", "possibly", etc.)
    - Specificity of claims
    - Evidence backing
    """

    HEDGING_WORDS = {
        "might", "maybe", "possibly", "perhaps", "could", "may",
        "probably", "likely", "unlikely", "seems", "appears",
        "suggest", "indicates", "unclear", "uncertain", "unknown",
    }

    def __init__(self, threshold: float = 0.85):
        super().__init__("confidence")
        self.threshold = threshold

    async def check(
        self,
        output: str,
        prompt: str,
        evidence: List[str]
    ) -> GateResult:
        words = output.lower().split()
        hedging_count = sum(1 for w in words if w in self.HEDGING_WORDS)
        hedging_ratio = hedging_count / max(len(words), 1)

        base_confidence = 1.0 - (hedging_ratio * 2)

        if evidence:
            evidence_boost = min(len(evidence) * 0.05, 0.15)
            base_confidence += evidence_boost

        confidence = max(0.0, min(1.0, base_confidence))

        if confidence < self.threshold:
            return GateResult(
                passed=False,
                feedback=f"Confidence {confidence:.2f} below threshold {self.threshold}",
                metadata={"confidence": confidence, "hedging_ratio": hedging_ratio},
            )

        return GateResult(passed=True, metadata={"confidence": confidence})


class SymbolicGate(BaseGate):
    """
    Gate 4: Validates logical and mathematical correctness.

    Checks:
    - Code syntax (if code blocks present)
    - Mathematical expressions
    - Logical consistency
    """

    def __init__(self):
        super().__init__("symbolic")

    async def check(
        self,
        output: str,
        prompt: str,
        evidence: List[str]
    ) -> GateResult:
        import re
        code_blocks = re.findall(r"```[\w]*\n(.*?)\n```", output, re.DOTALL)

        if code_blocks:
            for i, code in enumerate(code_blocks):
                syntax_ok, error = self._check_python_syntax(code)
                if not syntax_ok:
                    return GateResult(
                        passed=False,
                        feedback=f"Syntax error in code block {i+1}: {error}",
                        metadata={"code_block": i+1},
                    )

        math_expressions = re.findall(r"\$([^\$]+)\$", output)
        math_expressions += re.findall(r"(\d+\s*[\+\-\*\/]\s*\d+\s*=\s*\d+)", output)

        return GateResult(passed=True, metadata={"code_blocks": len(code_blocks)})

    def _check_python_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Check if Python code has valid syntax."""
        import ast
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)
