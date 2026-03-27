from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import CapabilityProbeResult, DeepGvrConfig, ModelSelection, ProbeStatus, RoutingMode
from .probes import probe_model_routing

_OPENROUTER_ROLE_DEFAULTS = {
    "generator": "claude-sonnet-4",
    "verifier": "deepseek-r1",
    "reviser": "claude-sonnet-4",
}

_ROLE_TEMPERATURES = {
    "generator": 0.7,
    "verifier": 0.2,
    "reviser": 0.4,
}


@dataclass(slots=True)
class EffectiveModelRoute:
    provider: str
    model: str
    routing_mode: RoutingMode = RoutingMode.DIRECT
    temperature: float | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RoutingPlan:
    strategy: RoutingMode
    probe: CapabilityProbeResult
    orchestrator: EffectiveModelRoute
    generator: EffectiveModelRoute
    verifier: EffectiveModelRoute
    reviser: EffectiveModelRoute
    limitations: list[str] = field(default_factory=list)


def build_routing_plan(
    config: DeepGvrConfig,
    routing_probe: CapabilityProbeResult | None = None,
) -> RoutingPlan:
    probe = routing_probe or probe_model_routing()
    orchestrator = _resolve_route("orchestrator", config.models.orchestrator)
    generator = _resolve_route("generator", config.models.generator)
    verifier = _resolve_route("verifier", config.models.verifier)
    reviser = _resolve_route("reviser", config.models.reviser, generator_route=generator)

    if probe.status is ProbeStatus.READY and not _same_model_path(generator, verifier):
        return RoutingPlan(
            strategy=RoutingMode.DIRECT,
            probe=probe,
            orchestrator=orchestrator,
            generator=generator,
            verifier=verifier,
            reviser=reviser,
        )

    if probe.status is ProbeStatus.READY:
        fallback_reason = (
            "Generator and verifier resolve to the same model path; applying prompt separation plus "
            "temperature decorrelation."
        )
        shared_route = generator
        fallback_limitations = [fallback_reason]
        reviser_route = reviser
    else:
        fallback_reason = probe.fallback
        shared_route = orchestrator
        fallback_limitations = [probe.summary]
        reviser_route = _temperature_route(shared_route, "reviser", fallback_reason)

    return RoutingPlan(
        strategy=RoutingMode.TEMPERATURE_DECORRELATION,
        probe=probe,
        orchestrator=orchestrator,
        generator=_temperature_route(shared_route, "generator", fallback_reason),
        verifier=_temperature_route(shared_route, "verifier", fallback_reason),
        reviser=reviser_route,
        limitations=fallback_limitations,
    )


def _resolve_route(
    role: str,
    selection: ModelSelection,
    *,
    generator_route: EffectiveModelRoute | None = None,
) -> EffectiveModelRoute:
    if role == "reviser" and selection.provider == "default" and not selection.model and generator_route is not None:
        return EffectiveModelRoute(
            provider=generator_route.provider,
            model=generator_route.model,
            notes=["Reviser defaulted to the generator route."],
        )

    provider = selection.provider or "default"
    model = selection.model.strip()
    notes: list[str] = []

    if not model:
        role_default = _role_default_model(provider, role)
        if role_default:
            model = role_default
            notes.append(f"Resolved the empty {role} model to the documented {provider} default.")
        elif provider == "default":
            model = "configured-by-hermes"
            notes.append("Resolved the empty model to the active Hermes default.")
        else:
            model = "provider-default"
            notes.append(f"Resolved the empty {role} model to the provider default path.")

    return EffectiveModelRoute(provider=provider, model=model, notes=notes)


def _role_default_model(provider: str, role: str) -> str | None:
    if provider == "openrouter":
        return _OPENROUTER_ROLE_DEFAULTS.get(role)
    return None


def _same_model_path(left: EffectiveModelRoute, right: EffectiveModelRoute) -> bool:
    return left.provider == right.provider and left.model == right.model


def _temperature_route(base: EffectiveModelRoute, role: str, reason: str) -> EffectiveModelRoute:
    notes = list(base.notes)
    notes.append(reason)
    return EffectiveModelRoute(
        provider=base.provider,
        model=base.model,
        routing_mode=RoutingMode.TEMPERATURE_DECORRELATION,
        temperature=_ROLE_TEMPERATURES[role],
        notes=notes,
    )
