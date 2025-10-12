# Tutorial de Instalação do TELia

Siga estes passos para configurar e rodar seu assistente de IA no Telegram.

### Pré-requisitos
1.  **n8n Auto-hospedado:** Você precisa ter uma instância do n8n (Community Edition) rodando. Pode ser no seu computador, em um servidor, etc.
2.  **Ngrok:** Se o seu n8n estiver rodando localmente, você precisará do `ngrok` para criar uma URL pública.

---

### Passo 1: Criar seu Bot no Telegram

A parte mais fácil!
1.  Abra o Telegram e procure por `@BotFather` (ele tem um selo de verificação azul).
2.  Inicie uma conversa com ele e digite `/newbot`.
3.  Siga as instruções: dê um nome para o seu bot (ex: "Meu Assistente Pessoal") e depois um nome de usuário (que deve terminar em `bot`, ex: `MeuAssisBot`).
4.  O BotFather vai te dar uma mensagem de sucesso e o mais importante: um **TOKEN DE API**. Copie este token e guarde-o em um lugar seguro. Ele é a senha do seu bot.

---

### Passo 2: Configurar o Workflow no n8n

1.  Na sua instância do n8n, crie um novo workflow.
2.  **Nó de Gatilho (Trigger):** Adicione o nó **"Telegram Trigger"**.
    - Em "Credentials", selecione "Create New".
    - No campo "Telegram API Token", cole o token que você pegou do BotFather.
    - Salve as credenciais.
3.  **Nó de IA:** Adicione o nó **"Google Gemini"** e configure sua chave de API do Google AI Studio (a mesma usada no projeto ZapIA).
    - Conecte a saída do "Telegram Trigger" na entrada do "Google Gemini".
    - No campo "Prompt" do Gemini, use uma expressão para pegar o texto da mensagem: `{{ $json.message.text }}`.
4.  **Nó de Resposta:** Adicione o nó **"Telegram"**.
    - As credenciais que você criou no passo 2 já estarão disponíveis, basta selecioná-las.
    - No campo "Chat ID", use a expressão `{{ $json.message.chat.id }}` para garantir que o bot responda na conversa correta.
    - No campo "Text", use uma expressão para pegar a resposta do Gemini: `{{ $nodes["Google Gemini"].json.candidates[0].content.parts[0].text }}`.
    - Conecte a saída do "Google Gemini" na entrada do nó "Telegram".
5.  **Ative o Workflow** clicando no botão "Active" no canto superior direito. O n8n vai gerar a URL do webhook para você.

---

### Passo 3: Ativar o Bot

1.  Volte para a conversa com o seu bot no Telegram.
2.  Envie uma mensagem para ele (ex: `/start` ou "Olá").
3.  Pronto! O gatilho no n8n será acionado, a mensagem passará pelo Gemini e a resposta será enviada de volta para você no Telegram.