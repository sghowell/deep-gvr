from __future__ import annotations

from abc import ABC, abstractmethod

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend, SimResults, SimSpec


class AnalysisAdapter(ABC):
    """Stable adapter boundary used by Tier 2 analysis mediation."""

    name: str

    @abstractmethod
    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        raise NotImplementedError


class SimulatorAdapter(ABC):
    """Legacy simulation-only boundary retained for internal Stim execution."""

    name: str

    @abstractmethod
    def run(self, spec: SimSpec, backend: Backend) -> SimResults:
        raise NotImplementedError
