1. Diagnóstico do ru_credentials                                                                                                                                                            
  A tabela existia e o código de save estava correto — a tabela estava simplesmente vazia porque ninguém havia usado o recurso ainda. Confirmado com um teste end-to-end que funcionou        
  perfeitamente.                                                                                                                                                                              
                                                                                                                                                                                              
  2. Novo módulo ru/booking.py — automação com Playwright:                                                                                                                                    
  - login_and_get_days(cpf, senha) — faz login no Keycloak, navega para a página de agendamento e extrai os dias disponíveis (tenta checkboxes → linhas de tabela → elementos com data-date)
  - book_days(cpf, senha, selected_values) — faz login, seleciona os checkboxes dos dias escolhidos e clica em submit                                                                         
                                                                                                                                                                                            
  3. Fluxo atualizado do /modo → Reservar Almoço:                                                                                                                                             
                                                                                                                                                                                              
  ┌─────────────────┬────────────────────────────────────────────────────────────────────────────┐                                                                                            
  │    Situação     │                               O que acontece                               │                                                                                            
  ├─────────────────┼────────────────────────────────────────────────────────────────────────────┤                                                                                            
  │ Sem credenciais │ Pede CPF → pede senha → salva → pergunta "quer reservar agora?"            │
  ├─────────────────┼────────────────────────────────────────────────────────────────────────────┤                                                                                            
  │ Com credenciais │ Mostra botões "Reservar agora" ou "Atualizar credenciais"                  │                                                                                            
  ├─────────────────┼────────────────────────────────────────────────────────────────────────────┤                                                                                            
  │ Reservar agora  │ "Entrando no sistema..." → mostra dias disponíveis → user escolhe → agenda │                                                                                            
  └─────────────────┴────────────────────────────────────────────────────────────────────────────┘                                                                                            
                  
  4. Seleção de dias — o usuário pode dizer:                                                                                                                                                  
  - "todos" → agenda tudo
  - "1, 2, 3" → agenda os dias de número 1, 2 e 3 da lista   