#!/bin/bash
echo "=========================================="
echo "🚀 INICIANDO ATUALIZAÇÃO DA TELIA..."
echo "=========================================="

echo "🔄 1. Puxando código novo do GitHub..."
cd "/home/emanueca/Telegramia/TELia"
git pull origin main

echo "📦 2. Atualizando bibliotecas..."
source .venv/bin/activate
pip install -r requirements.txt

echo "♻️  3. Reiniciando o motor..."
# Mata o processo atual (main.py). O start_server.py liga de novo na hora!
pkill -f "python main.py"

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
echo "   1) cd /home/emanueca/Telegramia/TELia"
echo "   2) source .venv/bin/activate"
echo "   3) screen -S telia"
echo "   4) python start_server.py"
echo "==========================================================="