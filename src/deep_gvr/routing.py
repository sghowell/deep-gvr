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
    fallback_routes: list["EffectiveModelRoute"] = field(default_factory=list)


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


def build_live_routing_plan(
    config: DeepGvrConfig,
    routing_probe: CapabilityProbeResult | None = None,
) -> RoutingPlan:
    return _build_explicit_role_routing_plan(
        config,
        routing_probe=routing_probe,
        route_note=(
            "Using configured top-level live role routing; the subagent routing probe does not block "
            "separate Hermes chat calls."
        ),
        fallback_note=(
            "Live top-level role calls can prefer explicit configured provider/model paths even while "
            "Hermes subagent routing remains fallback-only."
        ),
    )


def build_native_role_routing_plan(
    config: DeepGvrConfig,
    routing_probe: CapabilityProbeResult | None = None,
) -> RoutingPlan:
    return _build_explicit_role_routing_plan(
        config,
        routing_probe=routing_probe,
        route_note=(
            "Using configured top-level native role routing; the delegated subagent probe does not block "
            "separate Codex role calls."
        ),
        fallback_note=(
            "Native Codex role calls can prefer explicit configured provider/model paths even while "
            "Hermes delegated subagent routing remains fallback-only."
        ),
    )


def resolve_routing_probe(mode: str) -> CapabilityProbeResult:
    normalized = mode.strip().lower()
    if normalized == "auto":
        return probe_model_routing()
    if normalized == "ready":
        return CapabilityProbeResult(
            name="per_subagent_model_routing",
            status=ProbeStatus.READY,
            summary="Routing probe forced to ready by CLI flag for delegated runtime planning.",
            preferred_outcome="Route generator and verifier to distinct providers or models.",
            fallback="If runtime behavior disagrees, revert to prompt separation plus temperature decorrelation.",
            details={"forced_by": "routing_probe_mode", "mode": normalized},
        )
    if normalized == "fallback":
        return CapabilityProbeResult(
            name="per_subagent_model_routing",
            status=ProbeStatus.FALLBACK,
            summary="Routing probe forced to fallback by CLI flag for delegated runtime planning.",
            preferred_outcome="Route generator and verifier to distinct providers or models.",
            fallback="Use prompt separation plus temperature decorrelation and record the limitation.",
            details={"forced_by": "routing_probe_mode", "mode": normalized},
        )
    raise ValueError(f"Unsupported routing probe mode {mode!r}.")


def _build_explicit_role_routing_plan(
    config: DeepGvrConfig,
    *,
    routing_probe: CapabilityProbeResult | None,
    route_note: str,
    fallback_note: str,
) -> RoutingPlan:
    probe = routing_probe or probe_model_routing()
    shared_plan = build_routing_plan(config, routing_probe=probe)

    generator_route = shared_plan.generator
    if _selection_has_live_route_intent(config.models.generator):
        generator_route = _live_route(
            _resolve_route("generator", config.models.generator),
            fallback_route=shared_plan.generator,
            live_note=route_note,
        )

    verifier_route = shared_plan.verifier
    if _selection_has_live_route_intent(config.models.verifier):
        verifier_route = _live_route(
            _resolve_route("verifier", config.models.verifier),
            fallback_route=shared_plan.verifier,
            live_note=route_note,
        )

    reviser_route = shared_plan.reviser
    reviser_selection_is_explicit = _selection_has_live_route_intent(config.models.reviser) or (
        _selection_has_live_route_intent(config.models.generator)
        and config.models.reviser.provider == "default"
        and not config.models.reviser.model.strip()
    )
    if reviser_selection_is_explicit:
        generator_preference = (
            _resolve_route("generator", config.models.generator)
            if _selection_has_live_route_intent(config.models.generator)
            else shared_plan.generator
        )
        reviser_route = _live_route(
            _resolve_route("reviser", config.models.reviser, generator_route=generator_preference),
            fallback_route=shared_plan.reviser,
            live_note=route_note,
        )

    uses_explicit_routes = any(
        not _same_model_path(primary, fallback)
        for primary, fallback in (
            (generator_route, shared_plan.generator),
            (verifier_route, shared_plan.verifier),
            (reviser_route, shared_plan.reviser),
        )
    )
    limitations = list(shared_plan.limitations)
    if uses_explicit_routes and probe.status is not ProbeStatus.READY:
        limitations.append(fallback_note)

    return RoutingPlan(
        strategy=RoutingMode.DIRECT if uses_explicit_routes else shared_plan.strategy,
        probe=probe,
        orchestrator=shared_plan.orchestrator,
        generator=generator_route,
        verifier=verifier_route,
        reviser=reviser_route,
        limitations=limitations,
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


def _selection_has_concrete_model(selection: ModelSelection) -> bool:
    return bool(selection.model.strip())


def _selection_has_live_route_intent(selection: ModelSelection) -> bool:
    return selection.provider != "default" or _selection_has_concrete_model(selection)


def _live_route(
    primary_route: EffectiveModelRoute,
    *,
    fallback_route: EffectiveModelRoute,
    live_note: str,
) -> EffectiveModelRoute:
    notes = list(primary_route.notes)
    fallback_routes: list[EffectiveModelRoute] = []
    if not _same_model_path(primary_route, fallback_route):
        notes.append(live_note)
        fallback_routes.append(
            EffectiveModelRoute(
                provider=fallback_route.provider,
                model=fallback_route.model,
                routing_mode=fallback_route.routing_mode,
                temperature=fallback_route.temperature,
                notes=list(fallback_route.notes),
            )
        )
    return EffectiveModelRoute(
        provider=primary_route.provider,
        model=primary_route.model,
        routing_mode=primary_route.routing_mode,
        temperature=primary_route.temperature,
        notes=notes,
        fallback_routes=fallback_routes,
    )


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
