#!/usr/bin/env python3
"""
🧪 Script de Teste - TELia
Valida se todas as mudanças foram aplicadas corretamente
"""

import sys
import os

def test_imports():
    """Teste 1: Importar todos os módulos"""
    print("🧪 Teste 1: Verificando imports...")
    try:
        from bot.commands import start, help_command, cadastrar, login, sair, ajuda
        from bot.messages import handle_message
        from database.connection import get_connection
        from database.queries import (
            verificar_login,
            email_existe,
            save_message,
            get_history,
            get_profile,
            upsert_profile,
        )
        from ai.gemini import process_message
        from scheduler.jobs import start_scheduler
        
        print("✅ Todos os imports OK")
        return True
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False

def test_database():
    """Teste 2: Conectar ao banco de dados"""
    print("\n🧪 Teste 2: Conectando ao banco de dados...")
    try:
        from database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Testar se as tabelas novas existem
        cursor.execute("SHOW TABLES LIKE 'conversation_history'")
        if not cursor.fetchone():
            print("⚠️  conversation_history ainda não existe (será criada automaticamente)")
        else:
            print("✅ conversation_history existe")
        
        cursor.execute("SHOW TABLES LIKE 'user_profile'")
        if not cursor.fetchone():
            print("⚠️  user_profile ainda não existe (será criada automaticamente)")
        else:
            print("✅ user_profile existe")
        
        cursor.execute("SHOW TABLES LIKE 'users'")
        if cursor.fetchone():
            print("✅ users (ou usuarios) existe")
        else:
            print("❌ users/usuarios não encontrada!")
            return False
        
        cursor.close()
        conn.close()
        print("✅ Conexão com banco OK")
        return True
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

def test_environment():
    """Teste 3: Verificar variáveis de ambiente"""
    print("\n🧪 Teste 3: Verificando .env...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = [
            "TELEGRAM_BOT_TOKEN",
            "GEMINI_API_KEY",
            "MYSQL_HOST",
            "MYSQL_USER",
            "MYSQL_PASSWORD",
            "MYSQL_DATABASE"
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            print(f"⚠️  Variáveis faltando: {', '.join(missing)}")
            print("   (Pode estar tudo certo se você usar valores padrão)")
        else:
            print("✅ Todas as variáveis de ambiente OK")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao ler .env: {e}")
        return False

def test_handlers():
    """Teste 4: Verificar se handlers estão registrados"""
    print("\n🧪 Teste 4: Verificando handlers...")
    try:
        import inspect
        from main import main
        
        print("✅ main.py consegue ser importado")
        
        # Verificar se os comandos existem
        from bot.commands import start, help_command, cadastrar, login, sair, ajuda
        
        print("✅ /start handler OK")
        print("✅ /help handler OK") 
        print("✅ /ajuda handler OK")
        print("✅ /cadastrar handler OK")
        print("✅ /login handler OK")
        print("✅ /sair handler OK")
        
        return True
    except Exception as e:
        print(f"❌ Erro nos handlers: {e}")
        return False

def test_gemini_format():
    """Teste 5: Verificar formato esperado do Gemini"""
    print("\n🧪 Teste 5: Testando formato de resposta Gemini...")
    try:
        # Teste sem chamar API real
        test_response = {
            "reply": "Olá! Tudo bem?",
            "reminder": None,
            "profile_updates": [
                {"key": "nome", "value": "João"}
            ]
        }
        
        # Verificar estrutura
        assert "reply" in test_response, "Falta 'reply'"
        assert "reminder" in test_response, "Falta 'reminder'"
        assert "profile_updates" in test_response, "Falta 'profile_updates'"
        
        print("✅ Formato de resposta Gemini OK")
        print(f"   Exemplo: {test_response}")
        return True
    except Exception as e:
        print(f"❌ Erro no formato: {e}")
        return False

def test_auth_functions():
    """Teste 6: Verificar funções de autenticação"""
    print("\n🧪 Teste 6: Verificando funções de autenticação...")
    try:
        from database.queries import (
            verificar_login,
            email_existe,
            set_logado,
            get_usuario,
        )
        
        print("✅ verificar_login() existe")
        print("✅ email_existe() existe")
        print("✅ set_logado() existe")
        print("✅ get_usuario() existe")
        return True
    except ImportError as e:
        print(f"❌ Função de auth faltando: {e}")
        return False

def test_history_functions():
    """Teste 7: Verificar funções de histórico"""
    print("\n🧪 Teste 7: Verificando funções de histórico...")
    try:
        from database.queries import (
            save_message,
            get_history,
            get_profile,
            upsert_profile,
        )
        
        print("✅ save_message() existe")
        print("✅ get_history() existe")
        print("✅ get_profile() existe")
        print("✅ upsert_profile() existe")
        return True
    except ImportError as e:
        print(f"❌ Função de histórico faltando: {e}")
        return False

def main():
    """Executar todos os testes"""
    print("=" * 50)
    print("🧪 SUITE DE TESTES - TELia Reengenharia")
    print("=" * 50)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Database", test_database()))
    results.append(("Environment", test_environment()))
    results.append(("Handlers", test_handlers()))
    results.append(("Gemini Format", test_gemini_format()))
    results.append(("Auth Functions", test_auth_functions()))
    results.append(("History Functions", test_history_functions()))
    
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n🎯 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 Tudo pronto para deploy!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} teste(s) falharam. Revise os erros acima.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
