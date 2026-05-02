# Sistema de Transferência de Almoço - TELia

## Visão Geral

O sistema de transferência de almoço permite que usuários do RU (Restaurante Universitário) compartilhem refeições entre si através do bot Telegram.

## Fluxo de Uso

### 1. **Comando Principal**: `/transferir_almoco`

Quando o usuário executa este comando, aparece o menu inicial com duas opções:
- 🍽️ **Enviar Almoço** - Para quem tem almoço e quer transferir
- 📥 **Receber Almoço** - Para quem quer receber almoço

---

## Enviar Almoço

### Fluxo 1: Enviar Direto
1. Usuário clica em "Enviar Almoço"
2. Sistema verifica se tem credenciais do RU salvas
   - ✅ Se tem: vai para opções de envio
   - ❌ Se não tem: pede para fazer login no RU
3. Usuário escolhe "Enviar Direto"
4. Sistema pede o CPF de destino
5. Sistema acessa o RU via Playwright e realiza a transferência

### Fluxo 2: Entrar no Listão
1. Usuário clica em "Enviar Almoço"
2. Sistema verifica credenciais (como acima)
3. Usuário escolhe "Entrar no Listão"
4. Sistema pede quanto tempo deseja ficar:
   - 24 horas
   - 13 horas
   - 5 horas
   - 2 horas
5. Usuário entra na fila como **oferecedor**
6. Sistema procura um **buscador** compatível
   - ✅ Se encontra: Ambos recebem notificação de match
   - ❌ Se não encontra: Usuário espera na fila até que alguém entre

---

## Receber Almoço

### Fluxo 1: Entrar no Listão
1. Usuário clica em "Receber Almoço"
2. Sistema verifica credenciais do RU
3. Usuário escolhe "Entrar no Listão"
4. Sistema pede quanto tempo deseja ficar (mesmas opções)
5. Usuário entra na fila como **buscador**
6. Sistema procura um **oferecedor** compatível
   - ✅ Se encontra: Ambos recebem notificação de match
   - ❌ Se não encontra: Usuário espera na fila

### Fluxo 2: Pendências
1. Usuário clica em "Receber Almoço" → "Pendências"
2. Sistema mostra transferências pendentes que o usuário recebeu
3. Usuário pode aceitar ou recusar cada uma

---

## Sistema de Listão (Fila)

### Como Funciona
- **Listão** é uma fila de espera para matching automático
- Usuários podem entrar como **oferecedor** (tem almoço) ou **buscador** (quer almoço)
- Quando um oferecedor e um buscador entram, o sistema faz automaticamente um match
- Ambos recebem notificação no chat com opção de aceitar ou recusar

### Tempo no Listão
Cada usuário escolhe quanto tempo quer ficar:
- **24h**: Fica até 24 horas buscando/oferecendo
- **13h**: Fica até 13 horas
- **5h**: Fica até 5 horas
- **2h**: Fica até 2 horas (mais rápido para quem tem pressa)

Após expiração do tempo, o usuário é automaticamente removido da fila.

---

## Login no RU

Quando o usuário não tem credenciais salvas, o sistema pede:
1. **CPF** (sem formatação)
2. **Senha** do RU

As credenciais são criptografadas e armazenadas no banco de dados.
Se já tiver feito login antes, o sistema usa as credenciais salvas.

---

## Dados Armazenados

### Tabelas Criadas

#### `lunch_queue` - Fila de Almoço
```sql
id              - ID único
user_id         - ID do usuário Telegram
mode            - 'offering' (oferecendo) ou 'seeking' (buscando)
cpf             - CPF do usuário
full_name       - Nome completo
time_window     - Tempo que quer ficar (24h, 13h, 5h, 2h)
entered_at      - Quando entrou na fila
expires_at      - Quando expira a entrada
active          - Se ainda está ativo
```

#### `lunch_transfers` - Registro de Transferências
```sql
id              - ID único da transferência
donor_id        - ID do doador
recipient_id    - ID do receptor
donor_cpf       - CPF do doador
recipient_cpf   - CPF do receptor
transfer_date   - Data da transferência (sempre "hoje")
status          - pending, accepted, rejected, completed
created_at      - Quando foi criada
updated_at      - Última atualização
completed_at    - Quando foi completada
```

#### `lunch_notifications` - Notificações
```sql
id              - ID único
user_id         - ID do usuário que recebe notificação
transfer_id     - ID da transferência relacionada
message_text    - Texto da notificação
sent_at         - Quando foi enviada
read_at         - Quando foi lida
```

---

## Fluxo Técnico do Matching

1. **Usuário A** entra na fila como buscador
2. **Usuário B** entra na fila como oferecedor
3. Sistema detecta o match
4. Cria registro em `lunch_transfers` com status `pending`
5. Envia notificação para ambos no Telegram
6. Usuários têm opção de aceitar ou recusar
7. Se aceitar: status → `accepted` e ambos saem da fila
8. Se recusar: status → `rejected` e voltam para a fila

---

## Integração com RU (Playwright)

O sistema usa Playwright para:
1. Acessar o portal do RU (https://ru.fw.iffarroupilha.edu.br)
2. Fazer login com CPF/senha
3. Acessar a página de agendamento
4. Acessar a página de transferência de agendamento
5. Executar a transferência para o CPF de destino

### Credenciais RU
As credenciais são:
- Armazenadas em `ru_credentials`
- Criptografadas com Fernet (cryptography)
- Usadas automaticamente quando necessário

---

## Testes

### Testar Envio Direto
```
1. /transferir_almoco
2. Enviar Almoço
3. Fazer Login no RU (ou usar credenciais salvas)
4. Enviar Direto
5. Digitar CPF de destino
6. Verificar se transferência foi realizada no RU
```

### Testar Listão
```
1. Usuário A: /transferir_almoco → Enviar → Listão → 2h
2. Usuário B: /transferir_almoco → Receber → Listão → 2h
3. Ambos recebem notificação de match
4. Ambos aceitam o match
5. Sistema cria transferência e ambos saem do listão
```

---

## Status do Projeto

✅ Tabelas de banco criadas
✅ Funções de acesso ao RU implementadas
✅ Queries de banco implementadas
✅ Handlers do menu bot implementados
✅ Sistema de notificações integrado
⚠️ Testes finais necessários

---

## Próximos Passos (Futuros)

- [ ] Implementar aceitação/recusa de transferências
- [ ] Sistema de ratings/feedback entre usuários
- [ ] Histórico de transferências
- [ ] Notificações por horário específico
- [ ] Admin panel para gerenciar fila
