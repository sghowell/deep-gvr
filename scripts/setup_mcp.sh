#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Check or print the Aristotle MCP setup expectations for deep-gvr.

Usage:
  scripts/setup_mcp.sh [--check] [--print-snippet]

Options:
  --check          Verify that the required Tier 3 environment variables are present.
  --print-snippet  Print a shell snippet showing the expected environment setup.
  --help           Show this help text.
EOF
}

print_snippet() {
  cat <<'EOF'
Export the Aristotle credentials before using Tier 3:

  export ARISTOTLE_API_KEY="your-api-key"

deep-gvr currently uses orchestrator-mediated formal verification. Aristotle transport
configuration remains environment-specific to your Hermes installation.
EOF
}

run_check() {
  if [[ -z "${ARISTOTLE_API_KEY:-}" ]]; then
    echo "ARISTOTLE_API_KEY is not set. Tier 3 formal verification will fall back to structured unavailability." >&2
    return 1
  fi

  echo "ARISTOTLE_API_KEY is set."
  echo "Tier 3 can proceed to the repo's orchestrator-mediated Aristotle boundary."
  return 0
}

check_only="false"
show_snippet="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)
      check_only="true"
      shift
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

if [[ "${show_snippet}" == "true" || "${check_only}" != "true" ]]; then
  print_snippet
fi

if [[ "${check_only}" == "true" ]]; then
  run_check
fi
