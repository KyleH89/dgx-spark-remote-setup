#!/usr/bin/env zsh
set -euo pipefail
setopt NULL_GLOB

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NAME="dgx-spark-remote-setup"

if [[ -n "${HERMES_PROFILE:-}" && -d "$HOME/.hermes/profiles/$HERMES_PROFILE" ]]; then
  TARGET="$HOME/.hermes/profiles/$HERMES_PROFILE/skills/$NAME"
else
  TARGET="$HOME/.hermes/skills/$NAME"
fi

rm -rf "$TARGET"
mkdir -p "$TARGET/references"
cp "$SKILL_DIR/SKILL.md" "$TARGET/SKILL.md"
cp "$SKILL_DIR/README.md" "$TARGET/README.md"
cp "$SKILL_DIR"/references/*.md "$TARGET/references/"

echo "Installed Hermes $NAME skill: $TARGET"
if [[ -z "${HERMES_PROFILE:-}" && -d "$HOME/.hermes/profiles" ]]; then
  echo "Note: Hermes profiles detected. To install into one of them:"
  echo "  HERMES_PROFILE=<profile-name> zsh $0"
fi
