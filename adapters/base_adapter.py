from __future__ import annotations

from abc import ABC, abstractmethod

from deep_gvr.contracts import Backend, SimResults, SimSpec


class SimulatorAdapter(ABC):
    """Stable adapter boundary used by simulator subagents."""

    name: str

    @abstractmethod
    def run(self, spec: SimSpec, backend: Backend) -> SimResults:
        raise NotImplementedError
