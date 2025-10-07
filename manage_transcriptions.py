#!/usr/bin/env python3
"""
Script para gerenciar e consultar transcrições na collection dedicada
"""
import sys
import codecs
import json
from pathlib import Path
from datetime import datetime

# Fix para Windows
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

def show_stats():
    """Mostrar estatísticas das transcrições"""
    print("📊 Estatísticas das Transcrições")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        db_service = DatabaseService()
        
        stats = db_service.get_transcription_stats()
        
        print(f"📈 Total de transcrições: {stats.get('total_transcriptions', 0)}")
        
        if stats.get('top_users'):
            print("\n👥 Top 10 usuários:")
            for i, user in enumerate(stats['top_users'][:10], 1):
                avg_conf = user.get('avg_confidence', 0)
                print(f"   {i:2d}. {user['_id']}: {user['count']} transcrições (conf: {avg_conf:.2f})")
        
        if stats.get('top_companies'):
            print("\n🏢 Top 10 empresas:")
            for i, company in enumerate(stats['top_companies'][:10], 1):
                print(f"   {i:2d}. {company['_id']}: {company['count']} transcrições")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        return False

def search_transcriptions(query_type, value, limit=10):
    """Buscar transcrições por diferentes critérios"""
    print(f"🔍 Buscando transcrições por {query_type}: {value}")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        db_service = DatabaseService()
        
        if query_type == "user":
            results = db_service.get_transcriptions_by_user(value, limit)
        elif query_type == "company":
            results = db_service.get_transcriptions_by_company(value, limit)
        elif query_type == "confidence":
            min_conf = float(value)
            results = db_service.search_transcriptions({
                "confidence": {"$gte": min_conf}
            }, limit)
        elif query_type == "date":
            # Buscar por data (formato: YYYY-MM-DD)
            results = db_service.search_transcriptions({
                "created_at": {
                    "$gte": datetime.fromisoformat(f"{value}T00:00:00"),
                    "$lt": datetime.fromisoformat(f"{value}T23:59:59")
                }
            }, limit)
        else:
            print(f"❌ Tipo de busca inválido: {query_type}")
            return False
        
        if not results:
            print("📭 Nenhuma transcrição encontrada")
            return True
        
        print(f"📊 Encontradas {len(results)} transcrições:")
        print()
        
        for i, transcription in enumerate(results, 1):
            print(f"📝 {i}. ID: {transcription.get('mensagem_id', 'N/A')}")
            print(f"   👤 Usuário: {transcription.get('user_id', 'N/A')}")
            print(f"   🏢 Empresa: {transcription.get('company_id', 'N/A')}")
            print(f"   📞 Contato: {transcription.get('contact_name', 'N/A')}")
            print(f"   🎯 Confiança: {transcription.get('confidence', 0):.2f}")
            print(f"   ⏱️ Duração: {transcription.get('audio_duration', 0):.1f}s")
            print(f"   📅 Data: {transcription.get('created_at', 'N/A')}")
            
            # Preview do texto
            text = transcription.get('transcription', {}).get('text', '')
            if text:
                preview = text[:100] + "..." if len(text) > 100 else text
                print(f"   💬 Texto: {preview}")
            
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na busca: {e}")
        return False

def export_transcriptions(query_type, value, output_file):
    """Exportar transcrições para arquivo JSON"""
    print(f"📤 Exportando transcrições por {query_type}: {value}")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        db_service = DatabaseService()
        
        if query_type == "user":
            results = db_service.get_transcriptions_by_user(value, 1000)
        elif query_type == "company":
            results = db_service.get_transcriptions_by_company(value, 1000)
        elif query_type == "all":
            results = db_service.search_transcriptions({}, 1000)
        else:
            print(f"❌ Tipo de exportação inválido: {query_type}")
            return False
        
        if not results:
            print("📭 Nenhuma transcrição encontrada para exportar")
            return True
        
        # Converter ObjectId para string
        for result in results:
            if '_id' in result:
                result['_id'] = str(result['_id'])
            if 'created_at' in result:
                result['created_at'] = result['created_at'].isoformat()
            if 'updated_at' in result:
                result['updated_at'] = result['updated_at'].isoformat()
        
        # Salvar arquivo
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {len(results)} transcrições exportadas para: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na exportação: {e}")
        return False

def main():
    """Menu principal"""
    if len(sys.argv) < 2:
        print("🎙️ Gerenciador de Transcrições")
        print("=" * 50)
        print("Uso:")
        print("  python manage_transcriptions.py stats")
        print("  python manage_transcriptions.py search <tipo> <valor> [limite]")
        print("  python manage_transcriptions.py export <tipo> <valor> <arquivo>")
        print()
        print("Tipos de busca/exportação:")
        print("  user <user_id>     - Por usuário")
        print("  company <company_id> - Por empresa")
        print("  confidence <valor> - Por confiança mínima")
        print("  date <YYYY-MM-DD>  - Por data")
        print("  all                - Todas (apenas export)")
        print()
        print("Exemplos:")
        print("  python manage_transcriptions.py stats")
        print("  python manage_transcriptions.py search user test_user_001 5")
        print("  python manage_transcriptions.py search confidence 0.8")
        print("  python manage_transcriptions.py export user test_user_001 user_transcriptions.json")
        return
    
    command = sys.argv[1].lower()
    
    if command == "stats":
        success = show_stats()
    elif command == "search":
        if len(sys.argv) < 4:
            print("❌ Uso: python manage_transcriptions.py search <tipo> <valor> [limite]")
            return
        query_type = sys.argv[2]
        value = sys.argv[3]
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 10
        success = search_transcriptions(query_type, value, limit)
    elif command == "export":
        if len(sys.argv) < 5:
            print("❌ Uso: python manage_transcriptions.py export <tipo> <valor> <arquivo>")
            return
        query_type = sys.argv[2]
        value = sys.argv[3]
        output_file = sys.argv[4]
        success = export_transcriptions(query_type, value, output_file)
    else:
        print(f"❌ Comando inválido: {command}")
        return
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()





