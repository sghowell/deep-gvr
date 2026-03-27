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
target_dir="${HOME}/.hermes/skills"
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
  ln -s "${repo_root}" "${install_path}"
fi

echo "Installed deep-gvr at ${install_path} using ${install_mode} mode."
echo "Next steps:"
echo "  1. Review ${install_path}/README.md for quickstart and evaluation commands."
echo "  2. Run ${install_path}/scripts/setup_mcp.sh --check if you plan to use Tier 3."
