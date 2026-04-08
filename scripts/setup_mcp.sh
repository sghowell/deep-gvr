#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Check or print the Aristotle MCP setup expectations for deep-gvr.

Usage:
  scripts/setup_mcp.sh [--install] [--check] [--print-snippet] [--config PATH]

Options:
  --install        Install the Aristotle MCP stanza into the target Hermes config.
  --check          Verify the Tier 3 environment and Hermes MCP config entry.
  --config PATH    Hermes config path. Default: ~/.hermes/config.yaml
  --print-snippet  Print a shell snippet showing the expected environment setup.
  --help           Show this help text.
EOF
}

print_snippet() {
  cat <<'EOF'
Add the Aristotle MCP server to ~/.hermes/config.yaml:

  mcp_servers:
    aristotle:
      command: "uvx"
      args:
        - "--from"
        - "git+https://github.com/septract/lean-aristotle-mcp"
        - "aristotle-mcp"
      env:
        ARISTOTLE_API_KEY: "${ARISTOTLE_API_KEY}"
      timeout: 300
      connect_timeout: 60

Export the Aristotle credentials before starting Hermes:

  export ARISTOTLE_API_KEY="your-api-key"

Then restart Hermes so it can discover the MCP tools from mcp_servers.aristotle.
If the Aristotle tools still do not appear, ensure the Hermes environment has the
Python `mcp` package installed.
EOF
}

install_config() {
  mkdir -p "$(dirname "${config_path}")"
  if [[ ! -f "${config_path}" ]]; then
    : > "${config_path}"
  fi

  python3 - "${config_path}" <<'PY'
from pathlib import Path
import sys

config_path = Path(sys.argv[1]).expanduser()
original_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
lines = original_text.splitlines()


def scan_structure():
    in_mcp_servers = False
    mcp_indent = None
    mcp_index = None
    in_aristotle = False
    aristotle_indent = None
    aristotle_index = None
    section_end = len(lines)

    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if stripped == "mcp_servers:":
            in_mcp_servers = True
            mcp_indent = indent
            mcp_index = index
            section_end = len(lines)
            in_aristotle = False
            aristotle_indent = None
            aristotle_index = None
            continue

        if in_mcp_servers and mcp_indent is not None and indent <= mcp_indent:
            section_end = index
            break

        if (
            in_mcp_servers
            and mcp_indent is not None
            and stripped.startswith("aristotle:")
            and indent > mcp_indent
        ):
            in_aristotle = True
            aristotle_indent = indent
            aristotle_index = index
            continue

        if in_aristotle and aristotle_indent is not None and indent <= aristotle_indent:
            in_aristotle = False
            aristotle_indent = None

    return mcp_index, mcp_indent, aristotle_index, section_end


mcp_index, mcp_indent, aristotle_index, section_end = scan_structure()
changed = False

new_block = [
    'aristotle:',
    '  command: "uvx"',
    '  args:',
    '    - "--from"',
    '    - "git+https://github.com/septract/lean-aristotle-mcp"',
    '    - "aristotle-mcp"',
    '  env:',
    '    ARISTOTLE_API_KEY: "${ARISTOTLE_API_KEY}"',
    '  timeout: 300',
    '  connect_timeout: 60',
]

if aristotle_index is None:
    if mcp_index is None:
        block_lines = ["mcp_servers:"] + [f"  {line}" for line in new_block]
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(block_lines)
        changed = True
    else:
        indent_prefix = " " * (mcp_indent + 2)
        inserted_lines = [f"{indent_prefix}{line}" for line in new_block]
        lines[section_end:section_end] = inserted_lines
        changed = True

result = "\n".join(lines)
if lines:
    result += "\n"
config_path.write_text(result, encoding="utf-8")

if changed:
    print(f"Installed mcp_servers.aristotle into {config_path}.")
else:
    print(f"mcp_servers.aristotle already present in {config_path}.")
PY
}

run_check() {
  if [[ -z "${ARISTOTLE_API_KEY:-}" ]]; then
    echo "ARISTOTLE_API_KEY is not set. Tier 3 formal verification will fall back to structured unavailability." >&2
    return 1
  fi

  if ! command -v hermes >/dev/null 2>&1; then
    echo "Hermes CLI is not installed or not on PATH." >&2
    return 1
  fi

  if [[ ! -f "${config_path}" ]]; then
    echo "Hermes config file not found at ${config_path}. Add mcp_servers.aristotle before using Tier 3." >&2
    return 1
  fi

  if ! python3 - "${config_path}" <<'PY'
import sys
from pathlib import Path

config_path = Path(sys.argv[1]).expanduser()
lines = config_path.read_text(encoding="utf-8").splitlines()
in_mcp_servers = False
mcp_indent = None
in_aristotle = False
aristotle_indent = None
has_transport = False

for raw_line in lines:
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    indent = len(raw_line) - len(raw_line.lstrip(" "))

    if stripped == "mcp_servers:":
        in_mcp_servers = True
        mcp_indent = indent
        in_aristotle = False
        aristotle_indent = None
        continue

    if in_mcp_servers and mcp_indent is not None and indent <= mcp_indent:
        in_mcp_servers = False
        in_aristotle = False
        aristotle_indent = None

    if in_mcp_servers and stripped.startswith("aristotle:") and mcp_indent is not None and indent > mcp_indent:
        in_aristotle = True
        aristotle_indent = indent
        continue

    if in_aristotle and aristotle_indent is not None and indent <= aristotle_indent:
        in_aristotle = False
        aristotle_indent = None

    if in_aristotle and aristotle_indent is not None and indent > aristotle_indent:
        if stripped.startswith("command:") or stripped.startswith("url:"):
            has_transport = True
            break

if not has_transport:
    sys.stderr.write(
        f"{config_path} does not define a usable mcp_servers.aristotle transport. "
        "Tier 3 will fall back to structured unavailability.\n"
    )
    raise SystemExit(1)
PY
  then
    return 1
  fi

  echo "ARISTOTLE_API_KEY is set."
  echo "Hermes config defines mcp_servers.aristotle at ${config_path}."
  echo "Tier 3 can proceed to the repo's orchestrator-mediated Aristotle boundary."
  return 0
}

check_only="false"
install_requested="false"
show_snippet="false"
hermes_home="${HERMES_HOME:-${HOME}/.hermes}"
config_path="${hermes_home}/config.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install)
      install_requested="true"
      shift
      ;;
    --check)
      check_only="true"
      shift
      ;;
    --config)
      config_path="$2"
      shift 2
      ;;
    --print-snippet)
      show_snippet="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "${show_snippet}" == "true" || ( "${install_requested}" != "true" && "${check_only}" != "true" ) ]]; then
  print_snippet
fi

if [[ "${install_requested}" == "true" ]]; then
  install_config
fi

if [[ "${check_only}" == "true" ]]; then
  run_check
fi
