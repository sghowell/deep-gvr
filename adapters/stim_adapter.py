from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_gvr.contracts import Backend, ModalConfig, SSHConfig, SimAnalysis, SimDataPoint, SimResults, SimSpec, Tier2Config

from adapters.base_adapter import SimulatorAdapter

try:
    import numpy as np
except ImportError:  # pragma: no cover - exercised through adapter error handling
    np = None

try:
    import pymatching
except ImportError:  # pragma: no cover - exercised through adapter error handling
    pymatching = None

try:
    import stim
except ImportError:  # pragma: no cover - exercised through adapter error handling
    stim = None


TASK_MAP = {
    ("surface_code", "rotated_memory_z"): "surface_code:rotated_memory_z",
    ("surface_code", "rotated_memory_x"): "surface_code:rotated_memory_x",
    ("repetition_code", "memory"): "repetition_code:memory",
}

CommandRunner = Callable[[Sequence[str], Path | None, float | None], subprocess.CompletedProcess[str]]


def _default_command_runner(
    command: Sequence[str],
    cwd: Path | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


class StimAdapter(SimulatorAdapter):
    name = "stim"

    def __init__(
        self,
        *,
        tier2_config: Tier2Config | None = None,
        repo_root: Path | None = None,
        command_runner: CommandRunner | None = None,
    ) -> None:
        self.tier2_config = tier2_config or Tier2Config()
        self.repo_root = (repo_root or REPO_ROOT).resolve()
        self.command_runner = command_runner or _default_command_runner

    def run(self, spec: SimSpec, backend: Backend) -> SimResults:
        start = perf_counter()
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        if backend is Backend.LOCAL:
            return self._run_local(spec, backend, timestamp, start)
        if backend is Backend.MODAL:
            return self._run_modal(spec, backend, timestamp, start)
        if backend is Backend.SSH:
            return self._run_ssh(spec, backend, timestamp, start)
        raise ValueError(f"Unsupported backend {backend!r}.")

    def _run_local(self, spec: SimSpec, backend: Backend, timestamp: str, start: float) -> SimResults:
        dependency_errors = self._dependency_errors()
        if dependency_errors:
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="missing_dependencies",
                errors=dependency_errors,
            )

        try:
            code_task = self._resolve_code_task(spec)
        except ValueError as exc:
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="unsupported_task",
                errors=[str(exc)],
            )

        if spec.task.noise_model != "depolarizing":
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="unsupported_noise_model",
                errors=[f"Unsupported noise model {spec.task.noise_model!r}; only 'depolarizing' is implemented."],
            )

        if spec.task.decoder != "pymatching":
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="unsupported_decoder",
                errors=[f"Unsupported decoder {spec.task.decoder!r}; only 'pymatching' is implemented."],
            )

        data: list[SimDataPoint] = []
        errors: list[str] = []
        for distance in spec.task.distance:
            rounds = self._resolve_rounds(spec.task.rounds_per_distance, distance)
            for error_rate in spec.task.error_rates:
                try:
                    data.append(
                        self._simulate_point(
                            code_task=code_task,
                            distance=distance,
                            rounds=rounds,
                            error_rate=error_rate,
                            shots=spec.task.shots_per_point,
                            decoder=spec.task.decoder,
                        )
                    )
                except Exception as exc:  # pragma: no cover - defensive runtime boundary
                    errors.append(
                        f"Simulation failed for distance={distance} error_rate={error_rate}: {type(exc).__name__}: {exc}"
                    )

        runtime_seconds = perf_counter() - start
        analysis = self._analyze(data) if data else SimAnalysis(
            threshold_estimate=None,
            threshold_method="no_data",
            below_threshold_distances=[],
            scaling_exponent=None,
        )
        return SimResults(
            simulator=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=runtime_seconds,
            backend=backend,
            data=data,
            analysis=analysis,
            errors=errors,
        )

    def _run_modal(self, spec: SimSpec, backend: Backend, timestamp: str, start: float) -> SimResults:
        modal = self.tier2_config.modal
        stub_path = self._resolve_repo_path(modal.stub_path)
        if not stub_path.exists():
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="backend_misconfigured",
                errors=[f"Modal stub path {stub_path} does not exist."],
            )

        with tempfile.TemporaryDirectory(prefix="deep-gvr-modal-") as tmpdir:
            workdir = Path(tmpdir)
            spec_path = workdir / "sim_spec.json"
            output_path = workdir / "sim_results.json"
            spec_path.write_text(json.dumps(spec.to_dict(), indent=2) + "\n", encoding="utf-8")

            command = [
                modal.cli_bin,
                "run",
                str(stub_path),
                "--spec",
                str(spec_path),
                "--backend",
                backend.value,
                "--output",
                str(output_path),
            ]
            error_result = self._run_backend_command(
                command=command,
                backend=backend,
                timestamp=timestamp,
                start=start,
                description="Modal Stim adapter command",
                cwd=self.repo_root,
                timeout=spec.resources.timeout_seconds,
            )
            if error_result is not None:
                return error_result

            return self._load_external_results(
                output_path=output_path,
                backend=backend,
                timestamp=timestamp,
                start=start,
            )

    def _run_ssh(self, spec: SimSpec, backend: Backend, timestamp: str, start: float) -> SimResults:
        ssh = self.tier2_config.ssh
        config_errors = self._ssh_config_errors(ssh)
        if config_errors:
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="backend_misconfigured",
                errors=config_errors,
            )

        remote_root = ssh.remote_workspace.rstrip("/")
        run_label = re.sub(r"[^0-9A-Za-z]+", "", timestamp) or "run"
        remote_run_dir = f"{remote_root}/.deep-gvr-remote/{run_label}"
        remote_spec_path = f"{remote_run_dir}/sim_spec.json"
        remote_output_path = f"{remote_run_dir}/sim_results.json"
        target = self._ssh_target(ssh)

        with tempfile.TemporaryDirectory(prefix="deep-gvr-ssh-") as tmpdir:
            workdir = Path(tmpdir)
            local_spec_path = workdir / "sim_spec.json"
            local_output_path = workdir / "sim_results.json"
            local_spec_path.write_text(json.dumps(spec.to_dict(), indent=2) + "\n", encoding="utf-8")

            mkdir_command = [*self._ssh_base_command(ssh), target, f"mkdir -p {shlex.quote(remote_run_dir)}"]
            copy_spec_command = [
                *self._scp_base_command(ssh),
                str(local_spec_path),
                f"{target}:{remote_spec_path}",
            ]
            remote_command = (
                f"cd {shlex.quote(remote_root)} && "
                f"{shlex.quote(ssh.python_bin)} adapters/stim_adapter.py "
                f"--spec {shlex.quote(remote_spec_path)} "
                f"--backend local "
                f"--output {shlex.quote(remote_output_path)}"
            )
            run_command = [*self._ssh_base_command(ssh), target, remote_command]
            fetch_results_command = [
                *self._scp_base_command(ssh),
                f"{target}:{remote_output_path}",
                str(local_output_path),
            ]

            for command, description in (
                (mkdir_command, "SSH backend remote directory setup"),
                (copy_spec_command, "SSH backend spec upload"),
                (run_command, "SSH backend remote simulation"),
                (fetch_results_command, "SSH backend results download"),
            ):
                error_result = self._run_backend_command(
                    command=command,
                    backend=backend,
                    timestamp=timestamp,
                    start=start,
                    description=description,
                    cwd=self.repo_root,
                    timeout=spec.resources.timeout_seconds,
                )
                if error_result is not None:
                    return error_result

            return self._load_external_results(
                output_path=local_output_path,
                backend=backend,
                timestamp=timestamp,
                start=start,
            )

    def _simulate_point(
        self,
        *,
        code_task: str,
        distance: int,
        rounds: int,
        error_rate: float,
        shots: int,
        decoder: str,
    ) -> SimDataPoint:
        circuit = stim.Circuit.generated(
            code_task,
            distance=distance,
            rounds=rounds,
            after_clifford_depolarization=error_rate,
        )
        detector_error_model = circuit.detector_error_model(decompose_errors=True)
        matcher = pymatching.Matching.from_detector_error_model(detector_error_model)
        sampler = circuit.compile_detector_sampler()
        detection_events, observable_flips = sampler.sample(shots=shots, separate_observables=True)
        predictions = matcher.decode_batch(detection_events)
        mismatches = np.not_equal(predictions.astype(bool), observable_flips.astype(bool))
        errors_observed = int(np.count_nonzero(mismatches))
        return SimDataPoint(
            distance=distance,
            rounds=rounds,
            physical_error_rate=error_rate,
            logical_error_rate=errors_observed / shots,
            shots=shots,
            errors_observed=errors_observed,
            decoder=decoder,
        )

    def _resolve_code_task(self, spec: SimSpec) -> str:
        key = (spec.task.code, spec.task.task_type)
        if key not in TASK_MAP:
            supported = ", ".join(f"{code}/{task_type}" for code, task_type in sorted(TASK_MAP))
            raise ValueError(
                f"Unsupported Stim task {spec.task.code!r}/{spec.task.task_type!r}. Supported combinations: {supported}."
            )
        return TASK_MAP[key]

    def _resolve_rounds(self, rounds_per_distance: str, distance: int) -> int:
        value = rounds_per_distance.strip().lower()
        if value.isdigit():
            return int(value)

        match = re.fullmatch(r"(?:(\d+)?)d", value)
        if match:
            multiplier = int(match.group(1) or "1")
            return multiplier * distance

        raise ValueError(f"Unsupported rounds_per_distance value {rounds_per_distance!r}.")

    def _analyze(self, data: list[SimDataPoint]) -> SimAnalysis:
        grouped: dict[float, list[SimDataPoint]] = {}
        for point in data:
            grouped.setdefault(point.physical_error_rate, []).append(point)

        monotonic_candidates: list[float] = []
        below_threshold_distances: set[int] = set()
        for error_rate, points in grouped.items():
            ordered = sorted(points, key=lambda item: item.distance)
            if len(ordered) < 2:
                continue
            if all(left.logical_error_rate > right.logical_error_rate for left, right in zip(ordered, ordered[1:])):
                monotonic_candidates.append(error_rate)
                below_threshold_distances.update(point.distance for point in ordered[1:])

        if monotonic_candidates:
            return SimAnalysis(
                threshold_estimate=None,
                threshold_method="monotonic_distance_improvement",
                below_threshold_distances=sorted(below_threshold_distances),
                scaling_exponent=None,
            )

        return SimAnalysis(
            threshold_estimate=None,
            threshold_method="no_crossing_detected",
            below_threshold_distances=[],
            scaling_exponent=None,
        )

    def _dependency_errors(self) -> list[str]:
        errors: list[str] = []
        if stim is None:
            errors.append("Python package 'stim' is not installed.")
        if pymatching is None:
            errors.append("Python package 'pymatching' is not installed.")
        if np is None:
            errors.append("Python package 'numpy' is not installed.")
        return errors

    def _ssh_config_errors(self, ssh: SSHConfig) -> list[str]:
        errors: list[str] = []
        if not ssh.host:
            errors.append("SSH backend requires verification.tier2.ssh.host to be configured.")
        if not ssh.remote_workspace:
            errors.append("SSH backend requires verification.tier2.ssh.remote_workspace to be configured.")
        if ssh.key_path:
            key_path = Path(ssh.key_path).expanduser()
            if not key_path.exists():
                errors.append(f"SSH key_path {key_path} does not exist.")
        if not ssh.python_bin:
            errors.append("SSH backend requires verification.tier2.ssh.python_bin to be configured.")
        return errors

    def _resolve_repo_path(self, path: str) -> Path:
        resolved = Path(path).expanduser()
        if not resolved.is_absolute():
            resolved = self.repo_root / resolved
        return resolved

    def _ssh_target(self, ssh: SSHConfig) -> str:
        if ssh.user:
            return f"{ssh.user}@{ssh.host}"
        return ssh.host

    def _ssh_base_command(self, ssh: SSHConfig) -> list[str]:
        command = ["ssh"]
        if ssh.key_path:
            command.extend(["-i", str(Path(ssh.key_path).expanduser())])
        return command

    def _scp_base_command(self, ssh: SSHConfig) -> list[str]:
        command = ["scp"]
        if ssh.key_path:
            command.extend(["-i", str(Path(ssh.key_path).expanduser())])
        return command

    def _run_backend_command(
        self,
        *,
        command: Sequence[str],
        backend: Backend,
        timestamp: str,
        start: float,
        description: str,
        cwd: Path,
        timeout: float | None,
    ) -> SimResults | None:
        try:
            completed = self.command_runner(command, cwd, timeout)
        except FileNotFoundError as exc:
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="backend_unavailable",
                errors=[f"{description} failed because {exc.filename!r} is not installed or not on PATH."],
            )
        except subprocess.TimeoutExpired:
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="backend_timeout",
                errors=[f"{description} timed out after {timeout} seconds."],
            )

        if completed.returncode == 0:
            return None

        errors = [f"{description} exited with code {completed.returncode}."]
        if completed.stderr.strip():
            errors.append(f"stderr: {completed.stderr.strip()}")
        if completed.stdout.strip():
            errors.append(f"stdout: {completed.stdout.strip()}")
        return self._error_result(
            backend=backend,
            timestamp=timestamp,
            runtime_seconds=perf_counter() - start,
            threshold_method="backend_command_failed",
            errors=errors,
        )

    def _load_external_results(
        self,
        *,
        output_path: Path,
        backend: Backend,
        timestamp: str,
        start: float,
    ) -> SimResults:
        if not output_path.exists():
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="backend_no_output",
                errors=[f"Backend did not create expected results file {output_path}."],
            )

        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            results = SimResults.from_dict(payload)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="backend_invalid_output",
                errors=[f"Backend results file {output_path} was invalid: {type(exc).__name__}: {exc}"],
            )

        results.backend = backend
        return results

    def _error_result(
        self,
        *,
        backend: Backend,
        timestamp: str,
        runtime_seconds: float,
        threshold_method: str,
        errors: list[str],
    ) -> SimResults:
        return SimResults(
            simulator=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=runtime_seconds,
            backend=backend,
            data=[],
            analysis=SimAnalysis(
                threshold_estimate=None,
                threshold_method=threshold_method,
                below_threshold_distances=[],
                scaling_exponent=None,
            ),
            errors=errors,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deep-gvr Stim adapter")
    parser.add_argument("--spec", required=True, help="Path to a simulation spec JSON file")
    parser.add_argument("--backend", required=True, choices=[item.value for item in Backend])
    parser.add_argument("--output", required=True, help="Path to write normalized results JSON")
    parser.add_argument("--modal-cli-bin", default="modal", help="Modal CLI binary used for the modal backend")
    parser.add_argument(
        "--modal-stub-path",
        default="adapters/modal_stubs/stim_modal.py",
        help="Repo-relative or absolute path to the Modal stub entrypoint",
    )
    parser.add_argument("--ssh-host", default="", help="SSH host used for the SSH backend")
    parser.add_argument("--ssh-user", default="", help="SSH user used for the SSH backend")
    parser.add_argument("--ssh-key-path", default="", help="SSH private key path used for the SSH backend")
    parser.add_argument(
        "--ssh-remote-workspace",
        default="",
        help="Remote repository workspace where adapters/stim_adapter.py is available",
    )
    parser.add_argument("--ssh-python-bin", default="python3", help="Python binary used on the remote SSH host")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    output_path = Path(args.output)
    spec = SimSpec.from_dict(json.loads(spec_path.read_text(encoding="utf-8")))

    tier2_config = Tier2Config(
        modal=ModalConfig(cli_bin=args.modal_cli_bin, stub_path=args.modal_stub_path),
        ssh=SSHConfig(
            host=args.ssh_host,
            user=args.ssh_user,
            key_path=args.ssh_key_path,
            remote_workspace=args.ssh_remote_workspace,
            python_bin=args.ssh_python_bin,
        ),
    )
    adapter = StimAdapter(tier2_config=tier2_config)
    results = adapter.run(spec, Backend(args.backend))
    output_path.write_text(json.dumps(results.to_dict(), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
