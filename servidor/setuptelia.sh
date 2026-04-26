#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

APT_UPDATED=0

run_with_privileges() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "[erro] Precisa de root ou sudo para instalar pacotes do sistema."
    exit 1
  fi
}

apt_update_once() {
  if [[ "$APT_UPDATED" -eq 0 ]]; then
    echo "[setup] Atualizando indice do apt..."
    run_with_privileges apt-get update -y
    APT_UPDATED=1
  fi
}

ensure_apt_package() {
  local pkg="$1"
  if dpkg -s "$pkg" >/dev/null 2>&1; then
    echo "[ok] Pacote ja instalado: $pkg"
    return
  fi

  apt_update_once
  echo "[setup] Instalando pacote faltante: $pkg"
  run_with_privileges apt-get install -y "$pkg"
}

echo "==========================================================="
echo " TELia setup - instalacao de dependencias faltantes"
echo "==========================================================="

ensure_apt_package git
ensure_apt_package python3
ensure_apt_package python3-pip
ensure_apt_package python3-venv
ensure_apt_package mysql-server
ensure_apt_package screen

if command -v systemctl >/dev/null 2>&1; then
  echo "[setup] Garantindo mysql ativo no boot..."
  run_with_privileges systemctl enable mysql || true
  run_with_privileges systemctl start mysql || true
fi

cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "[setup] Criando ambiente virtual em $ROOT_DIR/.venv"
  python3 -m venv .venv
else
  echo "[ok] Ambiente virtual ja existe."
fi

source .venv/bin/activate

echo "[setup] Atualizando pip no ambiente virtual..."
python -m pip install --upgrade pip

echo "[setup] Instalando dependencias Python do projeto..."
pip install -r requirements.txt

if grep -qi '^playwright' requirements.txt; then
  echo "[setup] Instalando navegador Chromium do Playwright..."
  python -m playwright install chromium

  echo "[setup] Instalando dependencias de sistema do Playwright (quando necessario)..."
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    python -m playwright install-deps chromium || true
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$ROOT_DIR/.venv/bin/python" -m playwright install-deps chromium || true
  else
    echo "[aviso] Sem sudo para instalar dependencias de sistema do Playwright."
  fi
fi

echo ""
echo "[concluido] Setup finalizado."
echo "Proximo passo: rode o deploy com o script do servidor, se desejar."
