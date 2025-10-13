# Guia de Criação do Bot e Workflow (TELia)

Siga estes passos para criar seu bot no Telegram e configurar o fluxo de automação no n8n.

### Pré-requisitos
Antes de começar, garanta que você completou todas as etapas do **[Guia de Instalação do Ambiente](./INSTALL.md)** e que o `n8n` e o `ngrok` estão rodando.

---

### Passo 1: Criar seu Bot no Telegram

A parte mais fácil!
1.  Abra o Telegram e procure por `@BotFather` (ele tem um selo de verificação azul).
2.  Inicie uma conversa com ele e digite `/newbot`.
3.  Siga as instruções:
    * Primeiro, dê um **Nome de Exibição** (ex: `TELia`).
    * Depois, escolha um **Nome de Usuário** único que termine em `bot` (ex: `MeuTELiaBot` ou `emanueca_telia_bot`).
4.  O BotFather vai te dar uma mensagem de sucesso e o mais importante: um **TOKEN DE API**. Copie este token e guarde-o em um lugar seguro. Ele é a senha do seu bot.

---

### Passo 2: Configurar o Workflow no n8n

1.  Acesse sua instância do n8n (`http://localhost:5678`) e crie um novo workflow em branco.

2.  **Nó de Gatilho (Trigger):**
    * Clique no `+` central e adicione o nó **`Telegram Trigger`**.
    * Na opção "Trigger On", selecione **`On Message`** ("Na mensagem").
    * Em "Credentials", selecione "Create New". Cole o **TOKEN** que você pegou do BotFather e salve.

3.  **Nó de IA (O Cérebro):**
    * Clique no `+` do nó do Telegram e adicione o nó **`Google Gemini`**.
    * Na opção "Operation", selecione **`Message a Model`** ("Envie uma mensagem a um modelo").
    * Em "Credentials", crie uma nova credencial usando sua chave de API do **Google AI Studio**.
    * No campo **`Model`**, selecione a versão mais recente disponível (ex: `gemini-1.5-pro-latest`).
    * No campo **`Prompt`**, entre no modo **`Expression`** e cole o seguinte para dar personalidade ao bot:
        ```
        Você é um assistente prestativo chamado TELia. Responda de forma concisa e amigável à pergunta do usuário.

        Usuário: {{ $json.message.text }}
        TELia:
        ```

4.  **Nó de Resposta (A Boca):**
    * Clique no `+` do nó do Gemini e adicione o nó **`Telegram`**.
    * Selecione as mesmas credenciais do Telegram que você já criou.
    * Na opção "Operation", selecione **`Send Message`** ("Enviar uma mensagem de texto").
    * No campo **`Chat ID`**, entre no modo **`Expression`** e cole:
        ```
        {{ $nodes["Telegram Trigger"].json.message.chat.id }}
        ```
    * No campo **`Text`**, entre no modo **`Expression`** e cole:
        ```
        {{ $nodes["Google Gemini"].json.candidates[0].content.parts[0].text }}
        ```
    * **Dica:** A forma mais segura de preencher as expressões acima é usando o método de **arrastar e soltar** os dados do painel esquerdo, após uma primeira execução de teste.

---

### Passo 3: Ativar o Bot

1.  No canto superior direito, clique no botão para deixar o workflow **`Active`** (ativo).
2.  **Salve** o workflow.
3.  Volte para a conversa com o seu bot no Telegram e envie uma mensagem.
4.  Pronto! O bot está vivo e responderá automaticamente.
