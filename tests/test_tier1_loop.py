from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import (
    AnalyticalCheck,
    AnalyticalStatus,
    Backend,
    DeepGvrConfig,
    SimAnalysis,
    SimResults,
    Tier2Report,
    Tier1Report,
    VerificationReport,
    VerificationVerdict,
)
from deep_gvr.tier1 import (
    GenerationRequest,
    RevisionRequest,
    SessionStore,
    SimulationRequest,
    Tier1LoopRunner,
    VerificationRequest,
)


def _candidate(hypothesis: str, *, revision_notes: list[str] | None = None):
    from deep_gvr.contracts import CandidateSolution

    return CandidateSolution(
        hypothesis=hypothesis,
        approach="Ground the claim in known surface-code literature.",
        technical_details=["Carry the claim through a structured Tier 1 check."],
        expected_results=["Either the claim survives verification or flaws are recorded."],
        assumptions=["The cited literature is relevant to the candidate."],
        limitations=["No simulator is invoked in Tier 1 tests."],
        references=["Fowler et al. 2012"],
        revision_notes=revision_notes or [],
    )


def _report(
    verdict: VerificationVerdict,
    *,
    flaws: list[str] | None = None,
    cannot_verify_reason: str | None = None,
) -> VerificationReport:
    flaws = flaws or []
    check_status = AnalyticalStatus.FAIL if verdict is VerificationVerdict.FLAWS_FOUND else AnalyticalStatus.PASS
    tier1 = Tier1Report(
        checks=[
            AnalyticalCheck(
                check="logical_consistency",
                status=check_status,
                detail="Tier 1 test harness detail.",
            )
        ],
        overall=verdict,
        flaws=list(flaws),
        caveats=[],
    )
    return VerificationReport(
        verdict=verdict,
        tier1=tier1,
        tier2=None,
        tier3=[],
        flaws=list(flaws),
        caveats=[],
        cannot_verify_reason=cannot_verify_reason,
    )


class Tier1LoopTests(unittest.TestCase):
    def _config(self, evidence_dir: str, *, max_iterations: int = 3) -> DeepGvrConfig:
        config = DeepGvrConfig()
        config.evidence.directory = evidence_dir
        config.loop.max_iterations = max_iterations
        config.models.generator.provider = "generator-provider"
        config.models.generator.model = "generator-model"
        config.models.verifier.provider = "verifier-provider"
        config.models.verifier.model = "verifier-model"
        config.models.reviser.provider = "reviser-provider"
        config.models.reviser.model = "reviser-model"
        return config

    def test_completed_run_creates_checkpoint_index_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = Tier1LoopRunner(self._config(tmpdir))
            calls: dict[str, int] = {"generate": 0, "verify": 0, "revise": 0}

            def generator(request: GenerationRequest):
                calls["generate"] += 1
                self.assertEqual(request.problem, "Check a Tier 1 claim")
                return _candidate("Initial hypothesis")

            def verifier(request: VerificationRequest):
                calls["verify"] += 1
                self.assertFalse(hasattr(request, "problem"))
                self.assertEqual(request.candidate.hypothesis, "Initial hypothesis")
                return _report(VerificationVerdict.VERIFIED)

            def reviser(request: RevisionRequest):
                calls["revise"] += 1
                return _candidate("Unexpected revision")

            result = runner.run(
                problem="Check a Tier 1 claim",
                literature_context=["Known threshold is sub-1%."],
                generator=generator,
                verifier=verifier,
                reviser=reviser,
                session_id="session_test_verified",
            )

            self.assertEqual(result.final_report.verdict, VerificationVerdict.VERIFIED)
            self.assertEqual(calls, {"generate": 1, "verify": 1, "revise": 0})

            checkpoint_path = Path(tmpdir) / "session_test_verified" / "checkpoint.json"
            index_path = Path(tmpdir) / "index.json"
            evidence_path = Path(tmpdir) / "session_test_verified.jsonl"
            self.assertTrue(checkpoint_path.exists())
            self.assertTrue(index_path.exists())
            self.assertTrue(evidence_path.exists())

            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["status"], "completed")
            self.assertEqual(checkpoint["final_verdict"], "VERIFIED")
            self.assertEqual(checkpoint["next_phase"], "complete")

            evidence = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual([item["phase"] for item in evidence], ["generate", "verify"])
            self.assertEqual(evidence[1]["provider"], "verifier-provider")

    def test_flaws_found_triggers_revision_then_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = Tier1LoopRunner(self._config(tmpdir))
            verify_calls = 0

            def generator(request: GenerationRequest):
                return _candidate("Initial hypothesis")

            def verifier(request: VerificationRequest):
                nonlocal verify_calls
                verify_calls += 1
                if verify_calls == 1:
                    return _report(VerificationVerdict.FLAWS_FOUND, flaws=["Missing support for the conclusion."])
                return _report(VerificationVerdict.VERIFIED)

            def reviser(request: RevisionRequest):
                self.assertEqual(request.iteration, 2)
                self.assertEqual(request.verification_report.flaws, ["Missing support for the conclusion."])
                return _candidate(
                    "Revised hypothesis",
                    revision_notes=["Filled the missing support for the conclusion."],
                )

            result = runner.run(
                problem="Check revision behavior",
                generator=generator,
                verifier=verifier,
                reviser=reviser,
                session_id="session_test_revise",
            )

            self.assertEqual(result.final_candidate.hypothesis, "Revised hypothesis")
            self.assertEqual(len(result.checkpoint.verdict_history), 2)
            self.assertEqual(result.checkpoint.verdict_history[0].verdict, VerificationVerdict.FLAWS_FOUND)
            self.assertEqual(result.checkpoint.verdict_history[1].verdict, VerificationVerdict.VERIFIED)

            evidence = runner.session_store.read_evidence("session_test_revise")
            self.assertEqual([record.phase for record in evidence], ["generate", "verify", "revise", "verify"])

    def test_cannot_verify_stops_without_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = Tier1LoopRunner(self._config(tmpdir))
            revise_calls = 0

            def generator(request: GenerationRequest):
                return _candidate("Initial hypothesis")

            def verifier(request: VerificationRequest):
                return _report(
                    VerificationVerdict.CANNOT_VERIFY,
                    cannot_verify_reason="The candidate omits the derivation needed for review.",
                )

            def reviser(request: RevisionRequest):
                nonlocal revise_calls
                revise_calls += 1
                return _candidate("Unexpected revision")

            result = runner.run(
                problem="Check cannot-verify behavior",
                generator=generator,
                verifier=verifier,
                reviser=reviser,
                session_id="session_test_cannot_verify",
            )

            self.assertEqual(result.checkpoint.status, "cannot_verify")
            self.assertEqual(result.checkpoint.final_verdict, "CANNOT_VERIFY")
            self.assertEqual(revise_calls, 0)

    def test_resume_reuses_last_complete_checkpoint_after_interrupted_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._config(tmpdir)
            store = SessionStore(tmpdir)
            runner = Tier1LoopRunner(config, session_store=store)
            generator_calls = 0
            verifier_calls = 0

            def generator(request: GenerationRequest):
                nonlocal generator_calls
                generator_calls += 1
                return _candidate("Resume-safe hypothesis")

            def crashing_verifier(request: VerificationRequest):
                nonlocal verifier_calls
                verifier_calls += 1
                raise RuntimeError("simulated verifier interruption")

            def reviser(request: RevisionRequest):
                return _candidate("Unexpected revision")

            with self.assertRaises(RuntimeError):
                runner.run(
                    problem="Exercise resume",
                    generator=generator,
                    verifier=crashing_verifier,
                    reviser=reviser,
                    session_id="session_resume_safe",
                )

            checkpoint = store.load_checkpoint("session_resume_safe")
            self.assertEqual(checkpoint.next_phase, "verify")
            self.assertEqual(checkpoint.current_iteration, 1)
            self.assertEqual(generator_calls, 1)
            self.assertEqual(verifier_calls, 1)

            def verifier(request: VerificationRequest):
                return _report(VerificationVerdict.VERIFIED)

            result = runner.resume(
                "session_resume_safe",
                generator=generator,
                verifier=verifier,
                reviser=reviser,
            )

            self.assertEqual(result.final_report.verdict, VerificationVerdict.VERIFIED)
            self.assertEqual(generator_calls, 1)
            evidence = store.read_evidence("session_resume_safe")
            self.assertEqual([record.phase for record in evidence], ["generate", "verify"])

    def test_iteration_budget_exhaustion_admits_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = Tier1LoopRunner(self._config(tmpdir, max_iterations=2))

            def generator(request: GenerationRequest):
                return _candidate("Initial hypothesis")

            def verifier(request: VerificationRequest):
                return _report(VerificationVerdict.FLAWS_FOUND, flaws=["Still unsupported."])

            def reviser(request: RevisionRequest):
                return _candidate(
                    f"Revision {request.iteration}",
                    revision_notes=["Attempted to address the unsupported claim."],
                )

            result = runner.run(
                problem="Exhaust the iteration budget",
                generator=generator,
                verifier=verifier,
                reviser=reviser,
                session_id="session_budget_exhausted",
            )

            self.assertEqual(result.checkpoint.status, "failed")
            self.assertEqual(result.checkpoint.final_verdict, "FLAWS_FOUND")
            self.assertEqual(len(result.checkpoint.verdict_history), 2)
            evidence = runner.session_store.read_evidence("session_budget_exhausted")
            self.assertEqual([record.phase for record in evidence], ["generate", "verify", "revise", "verify"])

    def test_simulation_request_runs_mediator_and_reverifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = Tier1LoopRunner(self._config(tmpdir))
            verify_calls = 0
            simulator_calls = 0

            def generator(request: GenerationRequest):
                return _candidate("Quantitative hypothesis")

            def verifier(request: VerificationRequest):
                nonlocal verify_calls
                verify_calls += 1
                if request.simulation_results is None:
                    return VerificationReport(
                        verdict=VerificationVerdict.FLAWS_FOUND,
                        tier1=Tier1Report(
                            checks=[
                                AnalyticalCheck(
                                    check="logical_consistency",
                                    status=AnalyticalStatus.UNCERTAIN,
                                    detail="Quantitative claim needs empirical support.",
                                )
                            ],
                            overall=VerificationVerdict.FLAWS_FOUND,
                            flaws=["Empirical evidence is required."],
                            caveats=[],
                        ),
                        tier2=Tier2Report(
                            simulation_requested=True,
                            reason="The claim predicts a logical error rate.",
                            simulation_spec={
                                "simulator": "stim",
                                "task": {
                                    "code": "surface_code",
                                    "task_type": "rotated_memory_z",
                                    "distance": [3, 5],
                                    "rounds_per_distance": "2d",
                                    "noise_model": "depolarizing",
                                    "error_rates": [0.003],
                                    "decoder": "pymatching",
                                    "shots_per_point": 100,
                                },
                                "resources": {
                                    "timeout_seconds": 120,
                                    "max_parallel": 1,
                                },
                            },
                            results=None,
                            interpretation=None,
                        ),
                        tier3=[],
                        flaws=["Empirical evidence is required."],
                        caveats=[],
                        cannot_verify_reason=None,
                    )

                self.assertIsNotNone(request.simulation_results)
                return VerificationReport(
                    verdict=VerificationVerdict.VERIFIED,
                    tier1=Tier1Report(
                        checks=[
                            AnalyticalCheck(
                                check="logical_consistency",
                                status=AnalyticalStatus.PASS,
                                detail="The empirical follow-up addressed the open claim.",
                            )
                        ],
                        overall=VerificationVerdict.VERIFIED,
                        flaws=[],
                        caveats=[],
                    ),
                    tier2=Tier2Report(
                        simulation_requested=True,
                        reason="The claim predicts a logical error rate.",
                        simulation_spec=None,
                        results=request.simulation_results.to_dict(),
                        interpretation="The simulated trend supports the candidate.",
                    ),
                    tier3=[],
                    flaws=[],
                    caveats=[],
                    cannot_verify_reason=None,
                )

            def reviser(request: RevisionRequest):
                return _candidate("Unexpected revision")

            def simulator(request: SimulationRequest):
                nonlocal simulator_calls
                simulator_calls += 1
                self.assertEqual(request.backend, Backend.LOCAL)
                return SimResults(
                    simulator="stim",
                    adapter_version="0.1.0",
                    timestamp="2026-03-26T11:00:00Z",
                    runtime_seconds=0.2,
                    backend=Backend.LOCAL,
                    data=[],
                    analysis=SimAnalysis(
                        threshold_estimate=0.003,
                        threshold_method="monotonic_distance_improvement",
                        below_threshold_distances=[5],
                        scaling_exponent=None,
                    ),
                    errors=[],
                )

            result = runner.run(
                problem="Check Tier 2 mediation",
                generator=generator,
                verifier=verifier,
                reviser=reviser,
                simulator=simulator,
                session_id="session_tier2_verify",
            )

            self.assertEqual(result.final_report.verdict, VerificationVerdict.VERIFIED)
            self.assertEqual(verify_calls, 2)
            self.assertEqual(simulator_calls, 1)
            self.assertIsNotNone(result.final_report.tier2)
            self.assertIsNotNone(result.final_report.tier2.results)

            checkpoint = runner.session_store.load_checkpoint("session_tier2_verify")
            self.assertGreaterEqual(len(checkpoint.artifacts), 2)
            evidence = runner.session_store.read_evidence("session_tier2_verify")
            self.assertEqual([record.phase for record in evidence], ["generate", "simulate", "verify"])
            self.assertIsNotNone(evidence[1].simulation_results)


if __name__ == "__main__":
    unittest.main()
