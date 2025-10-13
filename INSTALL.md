# Guia de Instalação do Ambiente (n8n + Ngrok)

Este guia detalha todos os passos para instalar e configurar as ferramentas necessárias para rodar o **TELia**. Siga as etapas na ordem correta para garantir que seu ambiente funcione sem problemas.

## Etapa 1: Pré-requisitos Fundamentais (Node.js)

O n8n precisa do Node.js para funcionar.

1.  **Acesse o Site Oficial:** Vá para [nodejs.org](https://nodejs.org/).
2.  **Baixe a Versão LTS:** Na página inicial, clique no botão que diz **LTS**. Esta é a versão mais estável.
3.  **Instale:** Execute o instalador e siga os passos padrão. O `npm` já vem incluído.
4.  **Verifique a Instalação:** Abra seu terminal (`cmd`, `PowerShell` ou `Terminal`) e rode os seguintes comandos para confirmar:
    ```bash
    node -v
    npm -v
    ```
    Você deve ver as versões de cada um aparecerem.

## Etapa 2: Solucionando Erro Comum do PowerShell (Apenas Windows)

Se o comando `npm` retornar um erro vermelho sobre "execução de scripts", siga estes passos:

1.  **Abra o PowerShell como Administrador:** No menu Iniciar, procure por `PowerShell`, clique com o botão direito e selecione "Executar como Administrador".
2.  **Execute o Comando de Permissão:** Cole o seguinte comando e pressione Enter:
    ```powershell
    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
    ```
3.  **Confirme:** Digite `S` e pressione Enter para aceitar a mudança.
4.  Feche o PowerShell de Administrador e abra um novo terminal normal. O `npm` agora deve funcionar.

## Etapa 3: Instalando o n8n

1.  **Instale o n8n:** No seu terminal, execute o seguinte comando. Isso pode levar alguns minutos.
    ```bash
    npm install n8n -g
    ```
2.  **Configure a Conta:** Inicie o n8n pela primeira vez com o comando:
    ```bash
    n8n
    ```
3.  Acesse `http://localhost:5678` no seu navegador e crie sua conta de "dono" (owner). Anote a senha que você criar.

## Etapa 4: Instalando e Configurando o Ngrok

1.  **Baixe o Ngrok:** Vá para [ngrok.com](https://ngrok.com/), crie uma conta gratuita e baixe o executável.
2.  **Autentique sua Conta:** Na sua dashboard do Ngrok, copie seu "authtoken". No terminal, execute o comando abaixo (só precisa ser feito uma vez):
    ```bash
    ngrok config add-authtoken SEU_TOKEN_AQUI
    ```

## Etapa 5: Iniciando o Ambiente para o Bot

Toda vez que for ligar seu bot, siga esta sequência:

1.  **Inicie o Ngrok:** Abra um terminal e rode:
    ```bash
    ngrok http 5678
    ```
2.  Copie a URL `https://...` que ele gerar na linha "Forwarding".

3.  **Inicie o n8n (com o Comando Correto):** Abra **outro** terminal e use o comando correspondente ao seu sistema operacional para iniciar o n8n, substituindo pela URL do Ngrok que você copiou.

    * **Para Windows (PowerShell):**
        ```powershell
        $env:WEBHOOK_URL="https://SUA_URL_DO_NGROK_AQUI/"
        n8n
        ```

    * **Para Windows (CMD - Prompt de Comando):**
        ```cmd
        set WEBHOOK_URL=https://SUA_URL_DO_NGROK_AQUI/
        n8n
        ```

    * **Para Linux ou macOS:**
        ```bash
        export WEBHOOK_URL=https://SUA_URL_DO_NGROK_AQUI/ && n8n
        ```
4.  Seu ambiente agora está online e pronto para receber mensagens!
