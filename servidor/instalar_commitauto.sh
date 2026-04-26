#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATER="$SCRIPT_DIR/atualizador.sh"
BASHRC="$HOME/.bashrc"
ALIAS_LINE="alias commitauto='$UPDATER'"

if [[ ! -f "$UPDATER" ]]; then
  printf 'Updater script not found at %s\n' "$UPDATER"
  exit 1
fi

if ! grep -Fqx "$ALIAS_LINE" "$BASHRC"; then
  printf '\n# TELia auto deploy command\n%s\n' "$ALIAS_LINE" >> "$BASHRC"
  printf 'Alias added to %s\n' "$BASHRC"
else
  printf 'Alias already exists in %s\n' "$BASHRC"
fi

printf 'To activate now, run: source ~/.bashrc\n'
printf 'Then use: commitauto\n'
