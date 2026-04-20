#!/usr/bin/env python3
"""
🧹 Script de Limpeza de Tabelas Duplicadas - TELia
Remove tabelas antigas em português (usuarios, lembretes)
"""

import sys
import os
from dotenv import load_dotenv
from database.connection import get_connection

load_dotenv()

def main():
    print("=" * 60)
    print("🧹 TELia - Remover Tabelas Duplicadas (PT-BR)")
    print("=" * 60)
    print()
    print("⚠️  AVISO: Este script vai DELETAR:")
    print("   • usuarios (tabela antiga em português)")
    print("   • lembretes (tabela antiga em português)")
    print()
    print("✅ As novas tabelas permanecerão:")
    print("   • users (nova)")
    print("   • reminders (nova)")
    print("   • conversation_history (nova)")
    print("   • user_profile (nova)")
    print()
    
    # Confirmação
    response = input("Digite 'sim' para prosseguir (ou Enter para cancelar): ").strip().lower()
    if response != "sim":
        print("❌ Operação cancelada.")
        return 1
    
    print()
    print("Conectando ao banco de dados...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Verificar tabelas
        print("\n📊 Tabelas atuais:")
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME
        """)
        
        tables_before = cursor.fetchall()
        for table in tables_before:
            print(f"   • {table[0]}")
        
        # 2. Contar registros
        print("\n📋 Registros a deletar:")
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        usuarios_count = cursor.fetchone()[0]
        print(f"   • usuarios: {usuarios_count} registros")
        
        cursor.execute("SELECT COUNT(*) FROM lembretes")
        lembretes_count = cursor.fetchone()[0]
        print(f"   • lembretes: {lembretes_count} registros")
        
        # 3. Confirmação final
        print()
        response = input("CONFIRMA a deleção? Digite 'deletar' para confirmar: ").strip().lower()
        if response != "deletar":
            print("❌ Operação cancelada.")
            cursor.close()
            conn.close()
            return 1
        
        # 4. Deletar
        print("\n🔄 Deletando...")
        
        cursor.execute("DROP TABLE IF EXISTS lembretes")
        print("   ✅ lembretes deletada")
        
        cursor.execute("DROP TABLE IF EXISTS usuarios")
        print("   ✅ usuarios deletada")
        
        conn.commit()
        
        # 5. Verificar resultado
        print("\n📊 Tabelas após limpeza:")
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME
        """)
        
        tables_after = cursor.fetchall()
        for table in tables_after:
            print(f"   • {table[0]}")
        
        # 6. Resumo
        print("\n" + "=" * 60)
        print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print()
        print("📊 Resumo:")
        print(f"   • Deletadas: {len(tables_before) - len(tables_after)} tabelas")
        print(f"   • Registros deletados: {usuarios_count + lembretes_count}")
        print(f"   • Tabelas restantes: {len(tables_after)}")
        print()
        print("🎉 Seu banco está agora limpo e compatível com esquema.bd!")
        
        cursor.close()
        conn.close()
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        print("\n💡 Dica: Verifique se as tabelas existem e se você tem permissão para deletá-las")
        return 1

if __name__ == "__main__":
    sys.exit(main())
