#!/usr/bin/env zsh
set -euo pipefail
setopt NULL_GLOB

DIR="$(cd "$(dirname "$0")" && pwd)"
zsh "$DIR/install-codex.sh"
zsh "$DIR/install-claude.sh"

# Hermes and Grok are optional harnesses — install only where present.
[[ -d "$HOME/.hermes" ]] && zsh "$DIR/install-hermes.sh"
[[ -d "$HOME/.grok" ]] && zsh "$DIR/install-grok.sh"
