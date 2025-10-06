#!/usr/bin/env python3
"""
Script para gerenciar downloads com falha (404, etc.)
"""
import sys
import codecs
from pathlib import Path
from datetime import datetime

# Fix para Windows
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

def list_failed_downloads():
    """Listar todos os downloads com falha"""
    print("❌ Downloads com Falha")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        from bson import ObjectId
        
        db_service = DatabaseService()
        db_service._ensure_initialized()
        
        # Buscar conversas com downloads falhados
        query = {
            "contacts.messages.download_status": "failed"
        }
        
        conversations = list(db_service.db.diarios.find(query))
        
        if not conversations:
            print("✅ Nenhum download com falha encontrado")
            return True
        
        total_failed = 0
        failed_by_type = {}
        
        print(f"📋 Encontradas {len(conversations)} conversas com downloads falhados")
        print()
        
        for i, conversation in enumerate(conversations, 1):
            conversation_id = str(conversation['_id'])
            user_name = conversation.get('user_name', 'Desconhecido')
            
            print(f"📁 [{i}/{len(conversations)}] {conversation_id[:8]} - {user_name}")
            
            # Processar cada contato
            for contact_idx, contact in enumerate(conversation.get('contacts', [])):
                contact_name = contact.get('contact_name', 'Unknown')
                
                # Processar cada mensagem
                for message_idx, message in enumerate(contact.get('messages', [])):
                    if message.get('download_status') == 'failed':
                        total_failed += 1
                        
                        # Classificar tipo de erro
                        error = message.get('download_error', 'Erro desconhecido')
                        if '404' in error:
                            error_type = '404 Not Found'
                        elif 'timeout' in error.lower():
                            error_type = 'Timeout'
                        elif 'connection' in error.lower():
                            error_type = 'Connection Error'
                        else:
                            error_type = 'Other'
                        
                        failed_by_type[error_type] = failed_by_type.get(error_type, 0) + 1
                        
                        print(f"   ❌ {contact_name}: {error_type}")
                        print(f"      📝 Erro: {error[:80]}...")
                        print(f"      📅 Data: {message.get('download_failed_at', 'N/A')}")
                        print()
        
        print("=" * 50)
        print("📊 Resumo dos Erros:")
        for error_type, count in failed_by_type.items():
            print(f"   {error_type}: {count} falhas")
        
        print(f"\n📈 Total de downloads falhados: {total_failed}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao listar downloads falhados: {e}")
        return False

def reset_failed_downloads():
    """Resetar status de downloads falhados para tentar novamente"""
    print("🔄 Resetando Downloads Falhados")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        from bson import ObjectId
        
        db_service = DatabaseService()
        db_service._ensure_initialized()
        
        # Buscar conversas com downloads falhados
        query = {
            "contacts.messages.download_status": "failed"
        }
        
        conversations = list(db_service.db.diarios.find(query))
        
        if not conversations:
            print("✅ Nenhum download com falha encontrado para resetar")
            return True
        
        total_reset = 0
        
        for conversation in conversations:
            conversation_id = str(conversation['_id'])
            
            # Resetar status de falha
            result = db_service.db.diarios.update_many(
                {"_id": ObjectId(conversation_id)},
                {
                    "$unset": {
                        "contacts.$[].messages.$[msg].download_status": "",
                        "contacts.$[].messages.$[msg].download_error": "",
                        "contacts.$[].messages.$[msg].download_failed_at": "",
                        "contacts.$[].messages.$[msg].404_error": ""
                    }
                },
                array_filters=[
                    {"msg.download_status": "failed"}
                ]
            )
            
            total_reset += result.modified_count
        
        print(f"✅ {total_reset} downloads resetados com sucesso")
        print("💡 Agora você pode executar o processamento novamente")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao resetar downloads falhados: {e}")
        return False

def show_failed_stats():
    """Mostrar estatísticas de downloads falhados"""
    print("📊 Estatísticas de Downloads Falhados")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        from bson import ObjectId
        
        db_service = DatabaseService()
        db_service._ensure_initialized()
        
        # Estatísticas gerais
        total_conversations = db_service.db.diarios.count_documents({})
        conversations_with_failed = db_service.db.diarios.count_documents({
            "contacts.messages.download_status": "failed"
        })
        
        # Contar total de downloads falhados
        pipeline = [
            {"$unwind": "$contacts"},
            {"$unwind": "$contacts.messages"},
            {"$match": {"contacts.messages.download_status": "failed"}},
            {"$count": "total_failed"}
        ]
        
        result = list(db_service.db.diarios.aggregate(pipeline))
        total_failed = result[0]['total_failed'] if result else 0
        
        # Estatísticas por tipo de erro
        pipeline = [
            {"$unwind": "$contacts"},
            {"$unwind": "$contacts.messages"},
            {"$match": {"contacts.messages.download_status": "failed"}},
            {"$group": {
                "_id": "$contacts.messages.download_error",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        error_stats = list(db_service.db.diarios.aggregate(pipeline))
        
        print(f"📈 Total de conversas: {total_conversations}")
        print(f"❌ Conversas com downloads falhados: {conversations_with_failed}")
        print(f"🎵 Total de downloads falhados: {total_failed}")
        
        if error_stats:
            print("\n🔍 Top 10 Erros:")
            for i, stat in enumerate(error_stats, 1):
                error = stat['_id'][:60] + "..." if len(stat['_id']) > 60 else stat['_id']
                print(f"   {i:2d}. {error} ({stat['count']} ocorrências)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        return False

def main():
    """Menu principal"""
    if len(sys.argv) < 2:
        print("❌ Gerenciador de Downloads Falhados")
        print("=" * 50)
        print("Uso:")
        print("  python manage_failed_downloads.py list")
        print("  python manage_failed_downloads.py stats")
        print("  python manage_failed_downloads.py reset")
        print()
        print("Comandos:")
        print("  list  - Listar todos os downloads com falha")
        print("  stats - Mostrar estatísticas de downloads falhados")
        print("  reset - Resetar status de downloads falhados")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        success = list_failed_downloads()
    elif command == "stats":
        success = show_failed_stats()
    elif command == "reset":
        print("⚠️  ATENÇÃO: Isso irá resetar TODOS os downloads falhados!")
        response = input("Deseja continuar? (s/N): ").strip().lower()
        if response in ['s', 'sim', 'y', 'yes']:
            success = reset_failed_downloads()
        else:
            print("❌ Operação cancelada")
            success = True
    else:
        print(f"❌ Comando inválido: {command}")
        return
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()



