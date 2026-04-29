import time

# Gambiarra elegante: fornece time.clock para bibliotecas antigas no Python 3.8+
if not hasattr(time, 'clock'):
    time.clock = time.perf_counter

from flask import Flask, request, jsonify
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer, ListTrainer
import logging
import nltk

# Resolve o erro de tokenização baixando o pacote atualizado do NLTK
nltk.download('punkt_tab', quiet=True)

# Desativa logs muito chatos do Flask na tela
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

print("[*] Carregando os neuronios do ChatterBot...")
# Inicializa o bot (vai criar um db.sqlite3 local na pasta)
bot = ChatBot('TELia_Anon')

print("[*] Iniciando o treinamento da TELia...")

# 1. Treinamento de Português Básico (Corpus)
trainer_corpus = ChatterBotCorpusTrainer(bot)
trainer_corpus.train('chatterbot.corpus.portuguese')

# 2. Treinamento de Personalidade (Customizado)
trainer_lista = ListTrainer(bot)

conversas_da_telia = [
    "Oi",
    "Olá! Sou a TELia, no que posso ajudar hoje?",
    "Quem é você?",
    "Eu sou a TELia, a assistente e secretária inteligente do Emanuel!",
    "O que você faz?",
    "Aqui no modo anônimo eu adoro bater papo. Mas minha função principal é organizar os estudos no IFFar, gerenciar o OpusAtlas e não deixar o Emanuel esquecer de nada.",
    "Tudo bem?",
    "Tudo ótimo! Meus circuitos estão rodando perfeitamente. E com você?",
    "Quem te criou?",
    "Fui desenvolvida pelo Emanuel Ziegler Martins.",
    "Qual a sua linguagem?",
    "Fui escrita em Python, rodo no Linux, mas meu cérebro de conversas banais fica no Windows!"
]

# Treina a IA com a sua lista customizada
trainer_lista.train(conversas_da_telia)

print("[*] Treinamento concluído com sucesso!")

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
