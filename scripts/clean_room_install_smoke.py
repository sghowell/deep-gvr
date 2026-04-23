#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(command)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def _fake_binary(path: Path, body: str = "#!/usr/bin/env bash\nexit 0\n") -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected mapping config payload in {path}")
    return payload


def _run_release_preflight(
    *,
    env: dict[str, str],
    skills_dir: Path,
    config_path: Path,
    hermes_config_path: Path,
) -> dict[str, object]:
    completed = _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "release_preflight.py"),
            "--json",
            "--skills-dir",
            str(skills_dir),
            "--config",
            str(config_path),
            "--hermes-config",
            str(hermes_config_path),
        ],
        env=env,
    )
    return json.loads(completed.stdout)


def _run_codex_preflight(
    *,
    env: dict[str, str],
    codex_skills_dir: Path,
    hermes_skills_dir: Path,
    config_path: Path,
    hermes_config_path: Path,
) -> dict[str, object]:
    completed = _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "codex_preflight.py"),
            "--json",
            "--codex-skills-dir",
            str(codex_skills_dir),
            "--hermes-skills-dir",
            str(hermes_skills_dir),
            "--config",
            str(config_path),
            "--hermes-config",
            str(hermes_config_path),
        ],
        env=env,
    )
    return json.loads(completed.stdout)


def _assert_ready(report: dict[str, object], *, expected_config_path: Path) -> None:
    if not bool(report.get("release_surface_ready")):
        raise RuntimeError(f"preflight report is not structurally ready: {json.dumps(report, indent=2)}")
    if str(expected_config_path) != report.get("config_path"):
        raise RuntimeError(
            f"preflight config path mismatch: expected {expected_config_path}, got {report.get('config_path')}"
        )


def _assert_runtime_config(
    *,
    config_path: Path,
    expected_backend: str,
    expected_runtime_home: Path,
) -> dict[str, object]:
    if not config_path.exists():
        raise RuntimeError(f"missing runtime config at {config_path}")
    payload = _load_yaml(config_path)
    runtime = payload.get("runtime")
    evidence = payload.get("evidence")
    if not isinstance(runtime, dict) or not isinstance(evidence, dict):
        raise RuntimeError(f"runtime config payload is missing runtime/evidence sections: {config_path}")
    backend = runtime.get("orchestrator_backend")
    if backend != expected_backend:
        raise RuntimeError(f"expected backend {expected_backend!r}, got {backend!r} in {config_path}")
    expected_directory = str(expected_runtime_home / "sessions")
    if evidence.get("directory") != expected_directory:
        raise RuntimeError(
            f"expected evidence directory {expected_directory!r}, got {evidence.get('directory')!r} in {config_path}"
        )
    return payload


def _hermes_clean_room() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="deep-gvr-clean-room-hermes-") as tmpdir:
        temp_root = Path(tmpdir)
        hermes_home = temp_root / "hermes-home"
        runtime_home = temp_root / "runtime-home"
        env = dict(os.environ)
        env["HOME"] = tmpdir
        env["HERMES_HOME"] = str(hermes_home)
        env["DEEP_GVR_HOME"] = str(runtime_home)

        _run(["bash", str(REPO_ROOT / "scripts" / "install.sh")], env=env)

        config_path = runtime_home / "config.yaml"
        config_payload = _assert_runtime_config(
            config_path=config_path,
            expected_backend="hermes",
            expected_runtime_home=runtime_home,
        )
        report = _run_release_preflight(
            env=env,
            skills_dir=hermes_home / "skills",
            config_path=config_path,
            hermes_config_path=hermes_home / "config.yaml",
        )
        _assert_ready(report, expected_config_path=config_path)
        return {
            "name": "hermes_clean_room",
            "status": "ready",
            "runtime_home": str(runtime_home),
            "config_path": str(config_path),
            "orchestrator_backend": config_payload["runtime"]["orchestrator_backend"],
            "release_overall_status": report["overall_status"],
            "release_surface_ready": report["release_surface_ready"],
        }


def _codex_hybrid_clean_room() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="deep-gvr-clean-room-codex-hybrid-") as tmpdir:
        temp_root = Path(tmpdir)
        hermes_home = temp_root / "hermes-home"
        codex_home = temp_root / "codex-home"
        runtime_home = temp_root / "runtime-home"
        bin_dir = temp_root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        _fake_binary(bin_dir / "codex")

        env = dict(os.environ)
        env["HOME"] = tmpdir
        env["HERMES_HOME"] = str(hermes_home)
        env["CODEX_HOME"] = str(codex_home)
        env["DEEP_GVR_HOME"] = str(runtime_home)
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

        _run(["bash", str(REPO_ROOT / "scripts" / "install_codex.sh")], env=env)

        config_path = runtime_home / "config.yaml"
        config_payload = _assert_runtime_config(
            config_path=config_path,
            expected_backend="hermes",
            expected_runtime_home=runtime_home,
        )
        release_report = _run_release_preflight(
            env=env,
            skills_dir=hermes_home / "skills",
            config_path=config_path,
            hermes_config_path=hermes_home / "config.yaml",
        )
        codex_report = _run_codex_preflight(
            env=env,
            codex_skills_dir=codex_home / "skills",
            hermes_skills_dir=hermes_home / "skills",
            config_path=config_path,
            hermes_config_path=hermes_home / "config.yaml",
        )
        _assert_ready(release_report, expected_config_path=config_path)
        _assert_ready(codex_report, expected_config_path=config_path)
        return {
            "name": "codex_hybrid_clean_room",
            "status": "ready",
            "runtime_home": str(runtime_home),
            "config_path": str(config_path),
            "orchestrator_backend": config_payload["runtime"]["orchestrator_backend"],
            "release_overall_status": release_report["overall_status"],
            "release_surface_ready": release_report["release_surface_ready"],
            "codex_overall_status": codex_report["overall_status"],
            "codex_surface_ready": codex_report["release_surface_ready"],
        }


def _codex_native_clean_room() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="deep-gvr-clean-room-codex-native-") as tmpdir:
        temp_root = Path(tmpdir)
        hermes_home = temp_root / "hermes-home"
        codex_home = temp_root / "codex-home"
        runtime_home = temp_root / "runtime-home"
        bin_dir = temp_root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        _fake_binary(bin_dir / "codex")

        env = dict(os.environ)
        env["HOME"] = tmpdir
        env["HERMES_HOME"] = str(hermes_home)
        env["CODEX_HOME"] = str(codex_home)
        env["DEEP_GVR_HOME"] = str(runtime_home)
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

        _run(["bash", str(REPO_ROOT / "scripts" / "install_codex.sh"), "--skip-hermes-install"], env=env)

        config_path = runtime_home / "config.yaml"
        config_payload = _assert_runtime_config(
            config_path=config_path,
            expected_backend="codex_local",
            expected_runtime_home=runtime_home,
        )
        release_report = _run_release_preflight(
            env=env,
            skills_dir=hermes_home / "skills",
            config_path=config_path,
            hermes_config_path=hermes_home / "config.yaml",
        )
        codex_report = _run_codex_preflight(
            env=env,
            codex_skills_dir=codex_home / "skills",
            hermes_skills_dir=hermes_home / "skills",
            config_path=config_path,
            hermes_config_path=hermes_home / "config.yaml",
        )
        _assert_ready(release_report, expected_config_path=config_path)
        _assert_ready(codex_report, expected_config_path=config_path)
        return {
            "name": "codex_native_clean_room",
            "status": "ready",
            "runtime_home": str(runtime_home),
            "config_path": str(config_path),
            "orchestrator_backend": config_payload["runtime"]["orchestrator_backend"],
            "release_overall_status": release_report["overall_status"],
            "release_surface_ready": release_report["release_surface_ready"],
            "codex_overall_status": codex_report["overall_status"],
            "codex_surface_ready": codex_report["release_surface_ready"],
        }


def run_clean_room_smoke() -> dict[str, object]:
    scenarios = [
        _hermes_clean_room(),
        _codex_hybrid_clean_room(),
        _codex_native_clean_room(),
    ]
    return {
        "overall_status": "ready",
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deep-gvr clean-room install and structural preflight smoke scenarios")
    parser.add_argument("--json", action="store_true", help="Emit the smoke summary as JSON")
    args = parser.parse_args()

    payload = run_clean_room_smoke()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"clean-room install smoke overall_status={payload['overall_status']}")
        for scenario in payload["scenarios"]:
            print(
                f"- {scenario['name']}: status={scenario['status']} "
                f"backend={scenario['orchestrator_backend']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
