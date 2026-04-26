#!/bin/bash
clear
echo "==========================================================="
echo "🚀 TELia - SISTEMA DE DEPLOY AUTOMÁTICO"
echo "==========================================================="

echo "🔄 1. Puxando novidades do GitHub..."
cd "/home/emanueca/Telegramia/TELia"
git pull origin main

echo "📦 2. Sincronizando bibliotecas..."
# Tenta ativar o ambiente. Se falhar, avisa o usuário.
source .venv/bin/activate || echo "⚠️ Alerta: Ambiente virtual não encontrado!"
pip install -r requirements.txt --quiet

echo "🌐 Verificando browser do Playwright..."
if ! python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    p.chromium.executable_path
" 2>/dev/null; then
    echo "   Browser ausente — baixando Chromium..."
    playwright install chromium
else
    echo "   Browser ok."
fi

echo "💀 3. Faxina de processos (Exorcizando fantasmas)..."

# 1. Mata os processos Python (Cérebro do Bot)
pkill -9 -f "main.py"
pkill -9 -f "start_server.py"

# 2. Mata todas as sessões do Screen que tenham 'telia' no nome
# Isso garante que não sobre nenhuma "sala" aberta
screen -ls | grep "\.telia" | cut -d. -f1 | awk '{print $1}' | xargs -r kill

# 3. Limpa as telas que ficaram com status 'Dead' (Lixo do sistema)
screen -wipe > /dev/null 2>&1

sleep 2

echo "🚀 4. Iniciando a TELia em uma nova sessão screen..."
# Inicia o bot em uma sessão chamada 'telia' de forma "desconectada" (-d -m)
screen -d -m -S telia bash -c "source .venv/bin/activate && python3 start_server.py"

echo "✅ Deploy concluído! O bot já está rodando em segundo plano."
echo "Para ver o que está acontecendo, digite: screen -r telia"

echo "✅ Deploy concluído com sucesso!"

echo ""
echo "==========================================================="
echo "🛠️  MANUAL DE SOBREVIVÊNCIA DO SERVIDOR"
echo "==========================================================="
echo "❌ ERRO 'COMMAND NOT FOUND'?"
echo "   Isso acontece porque o Python está 'escondido' no ambiente."
echo "   Sempre rode: source .venv/bin/activate"
echo ""
echo "📝 DICAS DO EDITOR NANO (Para editar arquivos):"
echo "   - Para SALVAR: Aperte Ctrl + O e depois ENTER"
echo "   - Para SAIR:   Aperte Ctrl + X"
echo ""
echo "📺 VER LOGS/TELA DO BOT:"
echo "   Execute: screen -r telia"
echo ""
echo "🚪 SAIR DA TELA (SEM DESLIGAR):"
echo "   No teclado: Ctrl + A, depois D"
echo ""
echo "🔌 O SERVIDOR REINICIOU? (COMO LIGAR TUDO):"
echo "   1. cd /home/emanueca/Telegramia/TELia"
echo "   2. source .venv/bin/activate  (Resolve o 'command not found')"
echo "   3. screen -S telia"
echo "   4. python start_server.py"
echo "==========================================================="
