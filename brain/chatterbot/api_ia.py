import time

# Gambiarra elegante: fornece time.clock para bibliotecas antigas no Python 3.8+
if not hasattr(time, 'clock'):
    time.clock = time.perf_counter

from flask import Flask, request, jsonify
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
import logging

# Desativa logs muito chatos do Flask na tela
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

print("[*] Carregando os neuronios do ChatterBot...")
# Inicializa o bot (vai criar um db.sqlite3 local na pasta)
bot = ChatBot('TELia_Anon')

# ATENÇÃO: Na PRIMEIRA vez que você rodar, descomente as duas linhas abaixo 
# para ele baixar o idioma português. Nas próximas vezes, pode deixar comentado para ligar mais rápido.
# trainer = ChatterBotCorpusTrainer(bot)
# trainer.train('chatterbot.corpus.portuguese')

@app.route('/chat', methods=['POST'])
def chat():
    dados = request.json
    # Pega o texto que o seu Linux mandou
    mensagem_usuario = dados.get('text') 
    
    if not mensagem_usuario:
        return jsonify({'error': 'Nenhum texto enviado'}), 400
        
    print(f"Recebido do Telegram: {mensagem_usuario}")
    
    # Gera a resposta do ChatterBot
    resposta_ia = bot.get_response(mensagem_usuario)
    print(f"TELia respondeu: {resposta_ia}")
    
    # Devolve para o Linux no formato que ele espera
    return jsonify({'reply': str(resposta_ia)})

if __name__ == '__main__':
    print("[V] Servidor Neural Online na porta 5000!")
    # O comando abaixo é o que "trava" a tela e mantem o programa rodando infinitamente
    app.run(host='0.0.0.0', port=5000)