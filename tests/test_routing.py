from __future__ import annotations

import unittest

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import CapabilityProbeResult, DeepGvrConfig, ProbeStatus, RoutingMode
from deep_gvr.routing import build_live_routing_plan, build_native_role_routing_plan, build_routing_plan, resolve_routing_probe


def _probe(status: ProbeStatus) -> CapabilityProbeResult:
    return CapabilityProbeResult(
        name="per_subagent_model_routing",
        status=status,
        summary="Test routing probe result.",
        preferred_outcome="Route generator and verifier to distinct providers or models.",
        fallback="Use prompt separation plus temperature decorrelation and record the limitation.",
        details={},
    )


class RoutingPlanTests(unittest.TestCase):
    def test_ready_probe_prefers_distinct_openrouter_defaults(self) -> None:
        config = DeepGvrConfig()
        plan = build_routing_plan(config, routing_probe=_probe(ProbeStatus.READY))

        self.assertEqual(plan.strategy, RoutingMode.DIRECT)
        self.assertEqual(plan.generator.provider, "openrouter")
        self.assertEqual(plan.generator.model, "claude-sonnet-4")
        self.assertEqual(plan.verifier.provider, "openrouter")
        self.assertEqual(plan.verifier.model, "deepseek-r1")
        self.assertEqual(plan.reviser.provider, "openrouter")
        self.assertEqual(plan.reviser.model, "claude-sonnet-4")

    def test_ready_probe_falls_back_when_generator_and_verifier_match(self) -> None:
        config = DeepGvrConfig()
        config.models.generator.provider = "openai"
        config.models.generator.model = "gpt-5.4"
        config.models.verifier.provider = "openai"
        config.models.verifier.model = "gpt-5.4"
        config.models.reviser.provider = "anthropic"
        config.models.reviser.model = "claude-3.7-sonnet"

        plan = build_routing_plan(config, routing_probe=_probe(ProbeStatus.READY))

        self.assertEqual(plan.strategy, RoutingMode.TEMPERATURE_DECORRELATION)
        self.assertEqual(plan.generator.provider, "openai")
        self.assertEqual(plan.generator.model, "gpt-5.4")
        self.assertEqual(plan.generator.temperature, 0.7)
        self.assertEqual(plan.verifier.temperature, 0.2)
        self.assertEqual(plan.verifier.routing_mode, RoutingMode.TEMPERATURE_DECORRELATION)
        self.assertEqual(plan.reviser.provider, "anthropic")
        self.assertEqual(plan.reviser.model, "claude-3.7-sonnet")
        self.assertEqual(plan.reviser.routing_mode, RoutingMode.DIRECT)
        self.assertIn("temperature decorrelation", plan.limitations[0].lower())

    def test_fallback_probe_uses_shared_orchestrator_route(self) -> None:
        config = DeepGvrConfig()
        config.models.orchestrator.provider = "openai"
        config.models.orchestrator.model = "gpt-5.4"

        plan = build_routing_plan(config, routing_probe=_probe(ProbeStatus.FALLBACK))

        self.assertEqual(plan.strategy, RoutingMode.TEMPERATURE_DECORRELATION)
        self.assertEqual(plan.generator.provider, "openai")
        self.assertEqual(plan.generator.model, "gpt-5.4")
        self.assertEqual(plan.generator.temperature, 0.7)
        self.assertEqual(plan.verifier.model, "gpt-5.4")
        self.assertEqual(plan.verifier.temperature, 0.2)
        self.assertEqual(plan.reviser.temperature, 0.4)
        self.assertEqual(plan.limitations, ["Test routing probe result."])

    def test_live_fallback_probe_prefers_explicit_role_routes_with_shared_fallback(self) -> None:
        config = DeepGvrConfig()
        config.models.generator.provider = "openrouter"
        config.models.generator.model = "claude-3.7-sonnet"
        config.models.verifier.provider = "openrouter"
        config.models.verifier.model = "deepseek-r1"

        plan = build_live_routing_plan(config, routing_probe=_probe(ProbeStatus.FALLBACK))

        self.assertEqual(plan.strategy, RoutingMode.DIRECT)
        self.assertEqual(plan.generator.provider, "openrouter")
        self.assertEqual(plan.generator.model, "claude-3.7-sonnet")
        self.assertEqual(plan.verifier.provider, "openrouter")
        self.assertEqual(plan.verifier.model, "deepseek-r1")
        self.assertEqual(plan.generator.fallback_routes[0].provider, "default")
        self.assertEqual(plan.generator.fallback_routes[0].model, "configured-by-hermes")
        self.assertEqual(plan.verifier.fallback_routes[0].provider, "default")
        self.assertEqual(plan.verifier.fallback_routes[0].model, "configured-by-hermes")
        self.assertTrue(any("top-level live role routing" in note.lower() for note in plan.verifier.notes))

    def test_live_fallback_probe_treats_provider_only_routes_as_explicit_live_intent(self) -> None:
        config = DeepGvrConfig()
        config.models.generator.provider = "openrouter"
        config.models.generator.model = ""
        config.models.verifier.provider = "openrouter"
        config.models.verifier.model = ""

        plan = build_live_routing_plan(config, routing_probe=_probe(ProbeStatus.FALLBACK))

        self.assertEqual(plan.strategy, RoutingMode.DIRECT)
        self.assertEqual(plan.generator.provider, "openrouter")
        self.assertEqual(plan.generator.model, "claude-sonnet-4")
        self.assertEqual(plan.verifier.provider, "openrouter")
        self.assertEqual(plan.verifier.model, "deepseek-r1")
        self.assertEqual(plan.generator.fallback_routes[0].provider, "default")
        self.assertEqual(plan.generator.fallback_routes[0].model, "configured-by-hermes")
        self.assertEqual(plan.verifier.fallback_routes[0].provider, "default")
        self.assertEqual(plan.verifier.fallback_routes[0].model, "configured-by-hermes")

    def test_native_fallback_probe_prefers_explicit_role_routes(self) -> None:
        config = DeepGvrConfig()
        config.models.generator.provider = "openrouter"
        config.models.generator.model = "claude-sonnet-4"
        config.models.verifier.provider = "openrouter"
        config.models.verifier.model = "deepseek-r1"

        plan = build_native_role_routing_plan(config, routing_probe=_probe(ProbeStatus.FALLBACK))

        self.assertEqual(plan.strategy, RoutingMode.DIRECT)
        self.assertEqual(plan.generator.provider, "openrouter")
        self.assertEqual(plan.generator.model, "claude-sonnet-4")
        self.assertEqual(plan.verifier.provider, "openrouter")
        self.assertEqual(plan.verifier.model, "deepseek-r1")
        self.assertTrue(any("native role routing" in note.lower() for note in plan.verifier.notes))
        self.assertTrue(any("native codex role calls" in item.lower() for item in plan.limitations))

    def test_resolve_routing_probe_ready_mode(self) -> None:
        probe = resolve_routing_probe("ready")
        self.assertEqual(probe.status, ProbeStatus.READY)
        self.assertEqual(probe.details["mode"], "ready")


if __name__ == "__main__":
    unittest.main()
