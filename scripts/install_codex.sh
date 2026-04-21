#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Install the deep-gvr Codex-local skill surface.

Usage:
  scripts/install_codex.sh [--target DIR] [--copy] [--force] [--skip-hermes-install]

Options:
  --target DIR           Target Codex skills directory. Default: ~/.codex/skills
  --copy                 Copy the Codex skill instead of creating a symlink.
  --force                Replace an existing deep-gvr Codex skill install in the target directory.
  --skip-hermes-install  Do not also install the underlying Hermes skill/runtime surface.
  --help                 Show this help text.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
codex_home="${CODEX_HOME:-${HOME}/.codex}"
hermes_home="${HERMES_HOME:-${HOME}/.hermes}"
target_dir="${codex_home}/skills"
codex_skill_source="${repo_root}/codex_skill"
hermes_install_path="${hermes_home}/skills/deep-gvr"
hermes_config_path="${hermes_home}/deep-gvr/config.yaml"
install_mode="symlink"
force="false"
skip_hermes_install="false"
hermes_install_state="unchanged"

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
    --skip-hermes-install)
      skip_hermes_install="true"
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
    echo "Refusing to replace existing Codex install at ${install_path} without --force." >&2
    exit 1
  fi
  rm -rf "${install_path}"
fi

if [[ "${install_mode}" == "copy" ]]; then
  cp -R "${codex_skill_source}" "${install_path}"
else
  mkdir -p "${install_path}"
  shopt -s dotglob nullglob
  for source_path in "${codex_skill_source}"/*; do
    ln -s "${source_path}" "${install_path}/$(basename "${source_path}")"
  done
  shopt -u dotglob nullglob
fi

if [[ "${skip_hermes_install}" != "true" ]]; then
  if [[ "${force}" == "true" ]]; then
    bash "${repo_root}/scripts/install.sh" --force
    hermes_install_state="refreshed"
  elif [[ ! -e "${hermes_install_path}" && ! -L "${hermes_install_path}" ]]; then
    bash "${repo_root}/scripts/install.sh"
    hermes_install_state="refreshed"
  elif [[ ! -f "${hermes_config_path}" ]]; then
    bash "${repo_root}/scripts/install.sh" --force
    hermes_install_state="refreshed"
  else
    echo "Leaving existing Hermes install at ${hermes_install_path} in place."
  fi
fi

echo "Installed deep-gvr Codex skill at ${install_path} using ${install_mode} mode."
if [[ "${skip_hermes_install}" == "true" ]]; then
  echo "Skipped underlying Hermes install at your request."
elif [[ "${hermes_install_state}" == "refreshed" ]]; then
  echo "Underlying Hermes skill/runtime install was refreshed."
else
  echo "Underlying Hermes skill/runtime install was already present and was left in place."
fi
echo "Next steps:"
echo "  1. Review ${repo_root}/docs/codex-local.md for the Codex-local operator flow."
echo "  2. Run 'uv run python ${repo_root}/scripts/codex_preflight.py --json' to inspect the Codex-local surface."
echo "  3. Run 'uv run python ${repo_root}/scripts/codex_preflight.py --operator' before live Codex operator use."
echo "  4. If you also use the Hermes /deep-gvr surface directly, keep using 'uv run python ${repo_root}/scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml'."
