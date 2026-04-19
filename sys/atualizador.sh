#!/bin/bash
echo "🔄 Puxando código novo do GitHub..."
cd "/home/emanueca/Telegramia/TELia"
git pull origin main

echo "📦 Atualizando bibliotecas (se houver)..."
source .venv/bin/activate
pip install -r requirements.txt

echo "♻️ Reiniciando o motor da TELia..."
# Mata o processo atual. O seu start_server.py vai perceber e ligar de novo na hora!
pkill -f "python main.py"

echo "✅ Deploy concluído! A TELia já está com o código novo."
