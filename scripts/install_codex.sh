#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Install the deep-gvr Codex-local skill surface.

Usage:
  scripts/install_codex.sh [--target DIR] [--plugin-root DIR] [--automation-root DIR] [--review-qa-root DIR] [--subagents-root DIR] [--ssh-devbox-root DIR] [--copy] [--force] [--skip-hermes-install]

Options:
  --target DIR           Target Codex skills directory. Default: ~/.codex/skills
  --plugin-root DIR      Export a standalone local Codex plugin marketplace root at DIR.
  --automation-root DIR  Export a standalone local Codex automation bundle at DIR.
  --review-qa-root DIR   Export a standalone local Codex review and visual-QA prompt bundle at DIR.
  --subagents-root DIR   Export a standalone local Codex subagent prompt bundle at DIR.
  --ssh-devbox-root DIR  Export a standalone local Codex SSH/devbox prompt bundle at DIR.
  --copy                 Copy the Codex skill instead of creating a symlink.
  --force                Replace an existing deep-gvr Codex skill install in the target directory.
  --skip-hermes-install  Do not also install the Hermes skill/runtime surface. Use this for Codex-native backend machines.
  --help                 Show this help text.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
codex_home="${CODEX_HOME:-${HOME}/.codex}"
hermes_home="${HERMES_HOME:-${HOME}/.hermes}"
target_dir="${codex_home}/skills"
codex_skill_source="${repo_root}/codex_skill"
codex_plugin_source="${repo_root}/plugins/deep-gvr"
codex_plugin_marketplace_source="${repo_root}/.agents/plugins/marketplace.json"
hermes_install_path="${hermes_home}/skills/deep-gvr"
hermes_config_path="${hermes_home}/deep-gvr/config.yaml"
install_mode="symlink"
force="false"
skip_hermes_install="false"
hermes_install_state="unchanged"
plugin_root=""
plugin_export_path=""
plugin_marketplace_path=""
automation_root=""
review_qa_root=""
subagents_root=""
ssh_devbox_root=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      target_dir="$2"
      shift 2
      ;;
    --plugin-root)
      plugin_root="$2"
      shift 2
      ;;
    --automation-root)
      automation_root="$2"
      shift 2
      ;;
    --review-qa-root)
      review_qa_root="$2"
      shift 2
      ;;
    --subagents-root)
      subagents_root="$2"
      shift 2
      ;;
    --ssh-devbox-root)
      ssh_devbox_root="$2"
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

if [[ -n "${plugin_root}" ]]; then
  plugin_export_path="${plugin_root}/plugins/deep-gvr"
  plugin_marketplace_path="${plugin_root}/.agents/plugins/marketplace.json"
  mkdir -p "$(dirname "${plugin_export_path}")"

  if [[ -e "${plugin_export_path}" || -L "${plugin_export_path}" ]]; then
    if [[ "${force}" != "true" ]]; then
      echo "Refusing to replace existing Codex plugin export at ${plugin_export_path} without --force." >&2
      exit 1
    fi
    rm -rf "${plugin_export_path}"
  fi

  if [[ -e "${plugin_marketplace_path}" || -L "${plugin_marketplace_path}" ]]; then
    if [[ "${force}" != "true" ]]; then
      echo "Refusing to replace existing Codex plugin marketplace at ${plugin_marketplace_path} without --force." >&2
      exit 1
    fi
    rm -f "${plugin_marketplace_path}"
  fi

  if [[ "${install_mode}" == "copy" ]]; then
    cp -R "${codex_plugin_source}" "${plugin_export_path}"
  else
    mkdir -p "${plugin_export_path}"
    shopt -s dotglob nullglob
    for source_path in "${codex_plugin_source}"/*; do
      ln -s "${source_path}" "${plugin_export_path}/$(basename "${source_path}")"
    done
    shopt -u dotglob nullglob
  fi

  mkdir -p "$(dirname "${plugin_marketplace_path}")"
  cp "${codex_plugin_marketplace_source}" "${plugin_marketplace_path}"
fi

if [[ -n "${automation_root}" ]]; then
  automation_args=(
    uv
    run
    python
    "${repo_root}/scripts/export_codex_automations.py"
    --output-root
    "${automation_root}"
  )
  if [[ "${force}" == "true" ]]; then
    automation_args+=(--force)
  fi
  "${automation_args[@]}"
fi

if [[ -n "${review_qa_root}" ]]; then
  review_args=(
    uv
    run
    python
    "${repo_root}/scripts/export_codex_review_qa.py"
    --output-root
    "${review_qa_root}"
  )
  if [[ "${force}" == "true" ]]; then
    review_args+=(--force)
  fi
  "${review_args[@]}"
fi

if [[ -n "${subagents_root}" ]]; then
  subagent_args=(
    uv
    run
    python
    "${repo_root}/scripts/export_codex_subagents.py"
    --output-root
    "${subagents_root}"
  )
  if [[ "${force}" == "true" ]]; then
    subagent_args+=(--force)
  fi
  "${subagent_args[@]}"
fi

if [[ -n "${ssh_devbox_root}" ]]; then
  ssh_devbox_args=(
    uv
    run
    python
    "${repo_root}/scripts/export_codex_ssh_devbox.py"
    --output-root
    "${ssh_devbox_root}"
  )
  if [[ "${force}" == "true" ]]; then
    ssh_devbox_args+=(--force)
  fi
  "${ssh_devbox_args[@]}"
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
if [[ -n "${plugin_root}" ]]; then
  echo "Exported the deep-gvr Codex plugin bundle to ${plugin_export_path}."
  echo "Exported local marketplace metadata to ${plugin_marketplace_path}."
fi
if [[ -n "${automation_root}" ]]; then
  echo "Exported the deep-gvr Codex automation bundle to ${automation_root}."
fi
if [[ -n "${review_qa_root}" ]]; then
  echo "Exported the deep-gvr Codex review/QA prompt bundle to ${review_qa_root}."
fi
if [[ -n "${subagents_root}" ]]; then
  echo "Exported the deep-gvr Codex subagent prompt bundle to ${subagents_root}."
fi
if [[ -n "${ssh_devbox_root}" ]]; then
  echo "Exported the deep-gvr Codex SSH/devbox prompt bundle to ${ssh_devbox_root}."
fi
if [[ "${skip_hermes_install}" == "true" ]]; then
  echo "Skipped Hermes install at your request."
elif [[ "${hermes_install_state}" == "refreshed" ]]; then
  echo "Hermes skill/runtime install was refreshed."
else
  echo "Hermes skill/runtime install was already present and was left in place."
fi
echo "Next steps:"
echo "  1. Review ${repo_root}/docs/codex-local.md for the Codex-local operator flow."
echo "  2. Run 'uv run python ${repo_root}/scripts/codex_preflight.py --json' to inspect the Codex-local surface."
echo "  3. Run 'uv run python ${repo_root}/scripts/codex_preflight.py --operator' before live Codex operator use."
echo "  4. If you want the packaged plugin bundle as well, review ${repo_root}/docs/codex-plugin.md."
echo "  5. If you want recurring Codex automation templates as well, review ${repo_root}/docs/codex-automations.md."
echo "  6. If you want the Codex review and visual-QA prompt kit as well, review ${repo_root}/docs/codex-review-qa.md."
echo "  7. If you want the Codex subagent prompt kit as well, review ${repo_root}/docs/codex-subagents.md."
echo "  8. If you want the Codex SSH/devbox remote-operator kit as well, review ${repo_root}/docs/codex-ssh-devbox.md."
echo "  9. If you also use the Hermes /deep-gvr surface or the Hermes backend, keep using 'uv run python ${repo_root}/scripts/release_preflight.py --operator --config \${DEEP_GVR_HOME:-\${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml'."
