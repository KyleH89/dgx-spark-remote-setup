#!/usr/bin/env zsh
set -euo pipefail
setopt NULL_GLOB

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NAME="dgx-spark-remote-setup"
TARGET="$HOME/.grok/skills/$NAME"

rm -rf "$TARGET"
mkdir -p "$TARGET/references"
cp "$SKILL_DIR/SKILL.md" "$TARGET/SKILL.md"
cp "$SKILL_DIR/README.md" "$TARGET/README.md"
cp "$SKILL_DIR"/references/*.md "$TARGET/references/"

echo "Installed Grok $NAME skill: $TARGET"
