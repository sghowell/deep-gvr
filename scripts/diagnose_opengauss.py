#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_gvr.formal import inspect_opengauss_transport


def _isoformat_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_doctor_command(
    *,
    command: list[str],
    cwd: Path,
    mode: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        return {
            "mode": mode,
            "command": command,
            "ready": False,
            "status": "missing_binary",
            "error": str(exc),
        }
    except OSError as exc:
        return {
            "mode": mode,
            "command": command,
            "ready": False,
            "status": "os_error",
            "error": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "mode": mode,
            "command": command,
            "ready": False,
            "status": "timeout",
            "error": f"OpenGauss doctor timed out after {timeout_seconds} seconds.",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }

    ready = completed.returncode == 0
    status = "ready" if ready else "error"
    return {
        "mode": mode,
        "command": command,
        "ready": ready,
        "status": status,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _probe_morph_target(target: str, *, timeout_seconds: int) -> dict[str, Any]:
    url = f"https://morph.new/{target}/yaml"
    request = urllib.request.Request(url, headers={"User-Agent": "deep-gvr-opengauss-diagnostics/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return {
                "target": target,
                "url": url,
                "ready": True,
                "status": "ready",
                "http_status": response.getcode(),
                "final_url": response.geturl(),
            }
    except urllib.error.HTTPError as exc:
        return {
            "target": target,
            "url": url,
            "ready": False,
            "status": "http_error",
            "http_status": exc.code,
            "final_url": exc.geturl(),
            "error": f"HTTP {exc.code}",
        }
    except urllib.error.URLError as exc:
        return {
            "target": target,
            "url": url,
            "ready": False,
            "status": "url_error",
            "error": str(exc.reason),
        }


def collect_opengauss_diagnostics(
    *,
    opengauss_root: Path | None = None,
    gauss_binary: str | Path = "gauss",
    gauss_config_path: Path | None = None,
    check_doctor: bool = True,
    check_morph: bool = True,
    morph_targets: list[str] | None = None,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    transport = inspect_opengauss_transport(
        opengauss_root=opengauss_root,
        gauss_binary=gauss_binary,
        gauss_config_path=gauss_config_path,
    )

    report: dict[str, Any] = {
        "generated_at": _isoformat_now(),
        "overall_status": "ready" if transport.ready else "blocked",
        "transport": {
            "ready": transport.ready,
            "opengauss_root": transport.opengauss_root,
            "opengauss_root_exists": transport.opengauss_root_exists,
            "install_script": transport.install_script,
            "install_script_exists": transport.install_script_exists,
            "local_launcher": transport.local_launcher,
            "local_launcher_exists": transport.local_launcher_exists,
            "runner_venv": transport.runner_venv,
            "runner_venv_exists": transport.runner_venv_exists,
            "gauss_binary": transport.gauss_binary,
            "gauss_available": transport.gauss_available,
            "gauss_config_path": transport.gauss_config_path,
            "gauss_config_exists": transport.gauss_config_exists,
        },
    }

    blocked = not transport.ready

    if check_doctor:
        doctor: dict[str, Any]
        root_path = Path(transport.opengauss_root)
        local_launcher = Path(transport.local_launcher)
        if transport.gauss_available:
            doctor = _run_doctor_command(
                command=[transport.gauss_binary, "doctor"],
                cwd=REPO_ROOT,
                mode="installed_binary",
                timeout_seconds=timeout_seconds,
            )
            if local_launcher.exists():
                report["raw_checkout_doctor_check"] = _run_doctor_command(
                    command=[str(local_launcher), "doctor"],
                    cwd=root_path,
                    mode="raw_checkout",
                    timeout_seconds=timeout_seconds,
                )
        else:
            doctor = _run_doctor_command(
                command=[str(local_launcher), "doctor"],
                cwd=root_path,
                mode="raw_checkout",
                timeout_seconds=timeout_seconds,
            )
        report["doctor_check"] = doctor
        if doctor.get("mode") == "installed_binary" and transport.ready:
            blocked = blocked or not bool(doctor.get("ready"))

    if check_morph:
        targets = morph_targets or ["opengauss", "opengauss-0-2-2"]
        morph_checks = [_probe_morph_target(target, timeout_seconds=timeout_seconds) for target in targets]
        report["morph_targets"] = morph_checks

    report["overall_status"] = "blocked" if blocked else "ready"
    return report


def _print_human_report(report: dict[str, Any]) -> None:
    transport = report["transport"]
    print("OpenGauss diagnostics")
    print(f"  overall_status: {report['overall_status']}")
    print(f"  gauss_available: {transport['gauss_available']}")
    print(f"  gauss_config_exists: {transport['gauss_config_exists']}")
    print(f"  opengauss_root: {transport['opengauss_root']}")
    print(f"  install_script_exists: {transport['install_script_exists']}")
    print(f"  local_launcher_exists: {transport['local_launcher_exists']}")
    print(f"  runner_venv_exists: {transport['runner_venv_exists']}")
    doctor = report.get("doctor_check")
    if isinstance(doctor, dict):
        print(f"- doctor_check: {doctor['status']}")
        print(f"  command: {' '.join(doctor.get('command', []))}")
        error = doctor.get("error")
        if error:
            print(f"  error: {error}")
        stdout = doctor.get("stdout")
        if stdout:
            print(f"  stdout: {stdout.strip()}")
        stderr = doctor.get("stderr")
        if stderr:
            print(f"  stderr: {stderr.strip()}")
    raw_checkout_doctor = report.get("raw_checkout_doctor_check")
    if isinstance(raw_checkout_doctor, dict):
        print(f"- raw_checkout_doctor_check: {raw_checkout_doctor['status']}")
        print(f"  command: {' '.join(raw_checkout_doctor.get('command', []))}")
        error = raw_checkout_doctor.get("error")
        if error:
            print(f"  error: {error}")
        stdout = raw_checkout_doctor.get("stdout")
        if stdout:
            print(f"  stdout: {stdout.strip()}")
        stderr = raw_checkout_doctor.get("stderr")
        if stderr:
            print(f"  stderr: {stderr.strip()}")
    morph_checks = report.get("morph_targets")
    if isinstance(morph_checks, list):
        for item in morph_checks:
            print(f"- morph:{item['target']}: {item['status']}")
            final_url = item.get("final_url")
            if final_url:
                print(f"  final_url: {final_url}")
            http_status = item.get("http_status")
            if http_status is not None:
                print(f"  http_status: {http_status}")
            error = item.get("error")
            if error:
                print(f"  error: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose local OpenGauss installer and runtime readiness")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text")
    parser.add_argument("--skip-doctor", action="store_true", help="Do not run gauss doctor during diagnostics")
    parser.add_argument("--skip-morph", action="store_true", help="Do not probe the published Morph targets")
    parser.add_argument("--opengauss-root", type=Path, help="OpenGauss checkout root. Default: ~/dev/OpenGauss")
    parser.add_argument("--gauss-binary", default="gauss", help="gauss binary or absolute path. Default: gauss")
    parser.add_argument("--gauss-config", type=Path, help="Gauss config path. Default: ~/.gauss/config.yaml")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=20,
        help="Timeout for doctor and Morph checks. Default: 20",
    )
    args = parser.parse_args()

    report = collect_opengauss_diagnostics(
        opengauss_root=args.opengauss_root,
        gauss_binary=args.gauss_binary,
        gauss_config_path=args.gauss_config,
        check_doctor=not args.skip_doctor,
        check_morph=not args.skip_morph,
        timeout_seconds=args.timeout_seconds,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human_report(report)

    return 0 if report["overall_status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
