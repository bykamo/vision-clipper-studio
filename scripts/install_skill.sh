#!/usr/bin/env bash
# Install the VisionClipper Agent Skill for AI coding agents.
#
# Usage:
#   ./scripts/install_skill.sh [claude|codex|hermes|copilot|agents|all] [--copy]
#
# Default: symlink (stays in sync with the repo). --copy copies the folder
# instead; then set VISION_CLIPPER_HOME so the helper can find the project.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/skills/vision-clipper"
TARGET="${1:-all}"
MODE="link"
[[ "${2:-}" == "--copy" || "${1:-}" == "--copy" ]] && MODE="copy"
[[ "$TARGET" == "--copy" ]] && TARGET="all"

declare -A DIRS=(
  [claude]="$HOME/.claude/skills"
  [codex]="$HOME/.codex/skills"
  [hermes]="$HOME/.hermes/skills"
  [copilot]="$HOME/.copilot/skills"
  [agents]="$HOME/.agents/skills"
)

install_one() {
  local name="$1" dir="${DIRS[$1]}"
  mkdir -p "$dir"
  local dest="$dir/vision-clipper"
  if [[ -e "$dest" || -L "$dest" ]]; then
    rm -rf "$dest"
  fi
  if [[ "$MODE" == "copy" ]]; then
    cp -R "$SRC" "$dest"
  else
    ln -s "$SRC" "$dest"
  fi
  echo "[OK] $name -> $dest ($MODE)"
}

if [[ "$TARGET" == "all" ]]; then
  for key in claude codex hermes copilot agents; do install_one "$key"; done
elif [[ -n "${DIRS[$TARGET]:-}" ]]; then
  install_one "$TARGET"
else
  echo "Unknown target: $TARGET (use claude|codex|hermes|copilot|agents|all)" >&2
  exit 1
fi

if [[ "$MODE" == "copy" ]]; then
  echo
  echo "Copied mode: add this to your shell profile so the helper finds the project:"
  echo "  export VISION_CLIPPER_HOME=\"$ROOT\""
fi
echo
echo "Verify: python3 \"$SRC/scripts/vclip.py\" doctor"
