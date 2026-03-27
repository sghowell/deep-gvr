from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Protocol

from .contracts import ProofStatus, Tier3ClaimResult


@dataclass(slots=True)
class FormalVerificationRequest:
    session_id: str
    iteration: int
    claims: list[Tier3ClaimResult]
    backend: str
    timeout_seconds: int


class FormalVerifier(Protocol):
    def __call__(self, request: FormalVerificationRequest) -> list[Tier3ClaimResult]:
        ...


class AristotleFormalVerifier:
    def __init__(
        self,
        executor: Callable[[FormalVerificationRequest], list[Tier3ClaimResult]] | None = None,
    ) -> None:
        self.executor = executor

    def __call__(self, request: FormalVerificationRequest) -> list[Tier3ClaimResult]:
        if request.backend != "aristotle":
            return self._results_for_claims(
                request,
                status=ProofStatus.ERROR,
                details=f"Unsupported formal backend {request.backend!r} for the Aristotle runner.",
                proof_time_seconds=0.0,
            )

        if self.executor is not None:
            try:
                return self.executor(request)
            except TimeoutError:
                return self._results_for_claims(
                    request,
                    status=ProofStatus.TIMEOUT,
                    details=(
                        "Aristotle formal verification timed out before a proof result was available."
                    ),
                    proof_time_seconds=float(request.timeout_seconds),
                )
            except Exception as exc:  # pragma: no cover - defensive runtime boundary
                return self._results_for_claims(
                    request,
                    status=ProofStatus.ERROR,
                    details=f"Aristotle formal verification failed: {type(exc).__name__}: {exc}",
                    proof_time_seconds=0.0,
                )

        if not os.getenv("ARISTOTLE_API_KEY"):
            return self._results_for_claims(
                request,
                status=ProofStatus.UNAVAILABLE,
                details="ARISTOTLE_API_KEY is not configured; formal verification is unavailable in this environment.",
                proof_time_seconds=0.0,
            )

        return self._results_for_claims(
            request,
            status=ProofStatus.UNAVAILABLE,
            details=(
                "Aristotle credentials are present, but repo-local transport is not wired. "
                "Use orchestrator mediation with an injected executor or Hermes MCP integration."
            ),
            proof_time_seconds=0.0,
        )

    def _results_for_claims(
        self,
        request: FormalVerificationRequest,
        *,
        status: ProofStatus,
        details: str,
        proof_time_seconds: float | None,
    ) -> list[Tier3ClaimResult]:
        return [
            Tier3ClaimResult(
                claim=claim.claim,
                backend=request.backend,
                proof_status=status,
                details=details,
                lean_code=claim.lean_code,
                proof_time_seconds=proof_time_seconds,
            )
            for claim in request.claims
        ]
