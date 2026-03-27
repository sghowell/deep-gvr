from __future__ import annotations

from pathlib import Path

from .contracts import DeepGvrConfig


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_domain_context(
    config: DeepGvrConfig,
    *,
    domain_override: str | None = None,
) -> tuple[str, list[str]]:
    domain = domain_override or config.domain.default
    files: list[Path] = []
    if config.domain.context_file:
        files.append(Path(config.domain.context_file).expanduser())
    else:
        domain_files = {
            "qec": _repo_root() / "domain" / "qec_context.md",
            "fbqc": _repo_root() / "domain" / "fbqc_context.md",
        }
        if domain in domain_files:
            files.append(domain_files[domain])
        if domain == "qec":
            files.append(_repo_root() / "domain" / "known_results.md")

    notes: list[str] = []
    for path in files:
        if not path.exists():
            raise FileNotFoundError(f"Configured domain context file {path} does not exist.")
        notes.extend(_markdown_notes(path.read_text(encoding="utf-8")))
    return domain, notes


def _markdown_notes(text: str) -> list[str]:
    notes: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(("- ", "* ")):
            notes.append(stripped[2:].strip())
        else:
            notes.append(stripped)
    return notes
