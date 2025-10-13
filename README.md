# TELia - IA Pessoal no Telegram

![GitHub repo size](https://img.shields.io/github/repo-size/emanueca/TELia?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/emanueca/TELia?style=for-the-badge)

### 💡 Crie sua versão

Diferente de outras plataformas, o Telegram permite a criação de bots de forma instantânea e gratuita, sem a necessidade de comprar um chip de celular ou passar por processos de aprovação de API.

**Vantagens deste projeto:**
- **100% Gratuito:** Não há custos escondidos.
- **Sem Chip:** Você não precisa de um número de telefone dedicado.
- **Setup Rápido:** Crie seu bot em menos de 5 minutos usando o `@BotFather`.
- **Privacidade Total:** Você hospeda o n8n e tem controle total sobre seus dados.

---

### 🚀 Como Começar

Para construir sua própria versão do TELia do zero, siga nosso guia passo a passo. É mais fácil do que você imagina!

➡️ **[TUTORIAL COMPLETO](./STEP.md)**

---

### ▶️ Inicializando o Servidor (Guia Rápido) &nbsp; [<sub>(não está entendendo nada? clique aqui)</sub>](./STEP.md)

Estes são os comandos para ligar o bot, depois que você já o configurou uma vez. Você precisará de **dois terminais do PowerShell** abertos.

**1. No primeiro terminal (para o Ngrok):**
   * Este comando cria o túnel seguro para a internet.
   ```powershell
   ngrok http 5678
   ```
   * Copie a URL `https://...` que aparecer na linha `Forwarding`.

**2. No segundo terminal (para o n8n):**
   * Primeiro, configure a URL do Ngrok que você acabou de copiar. Lembre-se das aspas e da barra `/` no final.
   ```powershell
   $env:WEBHOOK_URL="https://SUA_URL_DO_NGROK_AQUI/"
   ```
   * Depois, inicie o n8n.
   ```powershell
   n8n
   ```
Pronto! Com esses dois terminais rodando, seu bot está online e pronto para responder.

---

###  whatsapp  Procurando uma Versão para WhatsApp?

Se você precisa de uma solução mais robusta, com um foco mais profissional ou empresarial, ou simplesmente prefere o ecossistema do WhatsApp, confira nosso outro projeto:

➡️ **[ZapIA-API: Inteligência Artificial no WhatsApp](https://github.com/emanueca/zapIA-API)**

O ZapIA-API é um projeto mais avançado que ensina a lidar com a API do WhatsApp Business, incluindo os desafios de ter um número dedicado e gerenciar os custos da plataforma da Meta.

---
### 🤝 Contribuições

Sinta-se à vontade para abrir `Issues` com sugestões, reportar bugs ou enviar um Pull Request!
