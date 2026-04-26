#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "🚀 INICIANDO ATUALIZAÇÃO DA TELIA..."
echo "=========================================="

echo "🔄 1. Puxando código novo do GitHub..."
cd "$ROOT_DIR"
git pull origin main

echo "📦 2. Atualizando bibliotecas..."
if [[ ! -d ".venv" ]]; then
	echo "❌ Ambiente virtual .venv não encontrado em $ROOT_DIR"
	exit 1
fi
source .venv/bin/activate
pip install -r requirements.txt

echo "♻️  3. Reiniciando o motor..."
# Encerra tanto o launcher quanto o processo direto do bot.
pkill -f "start_server.py" || true
pkill -f "python.*main.py" || true

echo ""
echo "==========================================================="
echo "✅ DEPLOY CONCLUÍDO! O código novo já está rodando."
echo "==========================================================="
echo "🛠️  GUIA RÁPIDO DO SERVIDOR:"
echo ""
echo "👀 COMO VER A TELA DO BOT (Logs ao vivo):"
echo "   Digite: screen -r telia"
echo ""
echo "🚪 COMO SAIR DA TELA SEM DESLIGAR O BOT:"
echo "   No teclado: Aperte 'Ctrl + A', solte, e aperte 'D'"
echo ""
echo "🔌 SE O SERVIDOR DESLIGAR (Queda de energia/Reboot):"
echo "   Para ligar tudo do zero, rode em ordem:"
echo "   1) cd $ROOT_DIR"
echo "   2) source .venv/bin/activate"
echo "   3) screen -S telia"
echo "   4) python start_server.py"
echo "==========================================================="