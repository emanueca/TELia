#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="$SCRIPT_DIR/setuptelia.sh"
BASHRC="$HOME/.bashrc"
ALIAS_LINE="alias setuptelia='$SETUP_SCRIPT'"
GLOBAL_BIN="/usr/local/bin/setuptelia"

if [[ ! -f "$SETUP_SCRIPT" ]]; then
  echo "Script de setup nao encontrado em $SETUP_SCRIPT"
  exit 1
fi

if ! grep -Fqx "$ALIAS_LINE" "$BASHRC"; then
  printf '\n# TELia setup command\n%s\n' "$ALIAS_LINE" >> "$BASHRC"
  echo "Alias 'setuptelia' adicionado em $BASHRC"
else
  echo "Alias 'setuptelia' ja existe em $BASHRC"
fi

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  cat > "$GLOBAL_BIN" <<EOF
#!/usr/bin/env bash
"$SETUP_SCRIPT" "\$@"
EOF
  chmod +x "$GLOBAL_BIN"
  echo "Comando global instalado em $GLOBAL_BIN"
elif command -v sudo >/dev/null 2>&1; then
  sudo bash -c "cat > '$GLOBAL_BIN' <<'EOF'
#!/usr/bin/env bash
'$SETUP_SCRIPT' \"\$@\"
EOF"
  sudo chmod +x "$GLOBAL_BIN"
  echo "Comando global instalado em $GLOBAL_BIN"
else
  echo "[aviso] Sem sudo/root para criar $GLOBAL_BIN. Alias local foi configurado."
fi

echo "Para ativar agora: source ~/.bashrc"
echo "Depois rode: setuptelia"
