#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Install deep-gvr into a Hermes skills directory.

Usage:
  scripts/install.sh [--target DIR] [--copy] [--force]

Options:
  --target DIR  Target skills directory. Default: ~/.hermes/skills
  --copy        Copy the repository instead of creating a symlink.
  --force       Replace an existing deep-gvr install in the target directory.
  --help        Show this help text.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
hermes_home="${HERMES_HOME:-${HOME}/.hermes}"
target_dir="${hermes_home}/skills"
runtime_home="${DEEP_GVR_HOME:-${hermes_home}/deep-gvr}"
config_dir="${runtime_home}"
config_path="${config_dir}/config.yaml"
config_template="${repo_root}/templates/config.template.yaml"
config_materializer="${repo_root}/scripts/materialize_runtime_config.py"
install_mode="symlink"
force="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      target_dir="$2"
      shift 2
      ;;
    --copy)
      install_mode="copy"
      shift
      ;;
    --force)
      force="true"
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

mkdir -p "${target_dir}"
install_path="${target_dir}/deep-gvr"

if [[ -e "${install_path}" || -L "${install_path}" ]]; then
  if [[ "${force}" != "true" ]]; then
    echo "Refusing to replace existing install at ${install_path} without --force." >&2
    exit 1
  fi
  rm -rf "${install_path}"
fi

if [[ "${install_mode}" == "copy" ]]; then
  cp -R "${repo_root}" "${install_path}"
else
  mkdir -p "${install_path}"
  shopt -s dotglob nullglob
  for source_path in "${repo_root}"/*; do
    ln -s "${source_path}" "${install_path}/$(basename "${source_path}")"
  done
  shopt -u dotglob nullglob
fi

mkdir -p "${config_dir}"
if [[ ! -f "${config_path}" ]]; then
  python3 "${config_materializer}" \
    --template "${config_template}" \
    --output "${config_path}" \
    --orchestrator-backend hermes >/dev/null
  echo "Created default config at ${config_path}."
else
  echo "Leaving existing config at ${config_path} in place."
fi

echo "Installed deep-gvr at ${install_path} using ${install_mode} mode."
echo "Next steps:"
echo "  1. Review ${install_path}/README.md for quickstart, CLI, and evaluation commands."
echo "  2. Choose one environment sync path: 'uv sync' for the minimal local path, 'uv sync --all-extras' for the full validated portfolio, or a narrower extra sync if you only want part of Tier 2."
echo "  3. Run 'uv run python ${install_path}/scripts/release_preflight.py --json' to inspect the installed release surface."
echo "  4. Run 'uv run python ${install_path}/scripts/release_preflight.py --operator --config ${config_path}' before live operator use."
echo "  5. Run ${install_path}/scripts/setup_mcp.sh --install --check if you plan to use Tier 3."
echo "  6. Run ${install_path}/scripts/install_codex.sh if you also want the Codex-local surface."
