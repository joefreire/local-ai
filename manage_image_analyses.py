#!/usr/bin/env python3
"""
Script para gerenciar e consultar análises de imagem na collection dedicada
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
    """Mostrar estatísticas das análises de imagem"""
    print("📊 Estatísticas das Análises de Imagem")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        db_service = DatabaseService()
        
        # Garantir que o serviço está inicializado
        db_service._ensure_initialized()
        
        stats = db_service.get_image_analysis_stats()
        
        print(f"📈 Total de análises: {stats.get('total_analyses', 0)}")
        
        if stats.get('top_users'):
            print("\n👥 Top 10 usuários:")
            for i, user in enumerate(stats['top_users'][:10], 1):
                avg_time = user.get('avg_generation_time', 0)
                print(f"   {i:2d}. {user['_id']}: {user['count']} análises (tempo médio: {avg_time:.1f}s)")
        
        if stats.get('top_companies'):
            print("\n🏢 Top 10 empresas:")
            for i, company in enumerate(stats['top_companies'][:10], 1):
                print(f"   {i:2d}. {company['_id']}: {company['count']} análises")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        return False

def search_analyses(query_type, value, limit=10):
    """Buscar análises por diferentes critérios"""
    print(f"🔍 Buscando análises por {query_type}: {value}")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        db_service = DatabaseService()
        
        # Garantir que o serviço está inicializado
        db_service._ensure_initialized()
        
        query = {}
        if query_type == "user_id":
            query["user_id"] = value
        elif query_type == "company_id":
            query["company_id"] = value
        elif query_type == "conversation_id":
            query["conversation_id"] = value
        elif query_type == "contact_name":
            query["contact_name"] = {"$regex": value, "$options": "i"}
        elif query_type == "model":
            query["model"] = value
        else:
            print(f"❌ Tipo de busca não suportado: {query_type}")
            return False
        
        analyses = list(db_service.db.image_analyses.find(query).limit(limit))
        
        if not analyses:
            print("❌ Nenhuma análise encontrada")
            return False
        
        print(f"📋 Encontradas {len(analyses)} análises:")
        print("-" * 50)
        
        for i, analysis in enumerate(analyses, 1):
            mensagem_id = analysis.get('mensagem_id', 'N/A')
            contact_name = analysis.get('contact_name', 'N/A')
            model = analysis.get('model', 'N/A')
            created_at = analysis.get('created_at', 'N/A')
            description = analysis.get('image_description', 'N/A')
            
            print(f"{i:2d}. {mensagem_id[:12]} - {contact_name[:20]}")
            print(f"    🤖 Modelo: {model}")
            print(f"    📅 Data: {created_at}")
            print(f"    📝 Descrição: {description[:80]}...")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na busca: {e}")
        return False

def show_analysis_details(mensagem_id):
    """Mostrar detalhes completos de uma análise"""
    print(f"🔍 Detalhes da análise: {mensagem_id}")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        db_service = DatabaseService()
        
        # Garantir que o serviço está inicializado
        db_service._ensure_initialized()
        
        analysis = db_service.db.image_analyses.find_one({"mensagem_id": mensagem_id})
        
        if not analysis:
            print("❌ Análise não encontrada")
            return False
        
        print(f"📋 ID da Mensagem: {analysis.get('mensagem_id', 'N/A')}")
        print(f"👤 Contato: {analysis.get('contact_name', 'N/A')}")
        print(f"🏢 Empresa: {analysis.get('company_id', 'N/A')}")
        print(f"🤖 Modelo: {analysis.get('model', 'N/A')}")
        print(f"💻 Dispositivo: {analysis.get('device', 'N/A')}")
        print(f"📅 Criado em: {analysis.get('created_at', 'N/A')}")
        print(f"📊 Tamanho do arquivo: {analysis.get('file_size', 0)} bytes")
        print(f"⏱️ Tempo de geração: {analysis.get('generation_time', 0):.2f}s")
        
        print("\n📝 Descrição completa:")
        print("-" * 50)
        print(analysis.get('image_description', 'N/A'))
        
        print("\n🔧 Dados técnicos:")
        print("-" * 50)
        analysis_data = analysis.get('image_analysis', {})
        if analysis_data:
            print(f"   Prompt usado: {analysis_data.get('prompt_used', 'N/A')}")
            print(f"   Tempo de análise: {analysis_data.get('analysis_time', 0):.2f}s")
            print(f"   Tempo de download: {analysis_data.get('download_time', 0):.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao obter detalhes: {e}")
        return False

def export_analyses(output_file, limit=100):
    """Exportar análises para arquivo JSON"""
    print(f"📤 Exportando análises para: {output_file}")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        db_service = DatabaseService()
        
        # Garantir que o serviço está inicializado
        db_service._ensure_initialized()
        
        analyses = list(db_service.db.image_analyses.find({}).limit(limit))
        
        if not analyses:
            print("❌ Nenhuma análise encontrada para exportar")
            return False
        
        # Converter ObjectId para string
        for analysis in analyses:
            if '_id' in analysis:
                analysis['_id'] = str(analysis['_id'])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analyses, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ {len(analyses)} análises exportadas para {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na exportação: {e}")
        return False

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerenciar análises de imagem")
    parser.add_argument("--stats", action="store_true", help="Mostrar estatísticas")
    parser.add_argument("--search", choices=["user_id", "company_id", "conversation_id", "contact_name", "model"], 
                       help="Tipo de busca")
    parser.add_argument("--value", type=str, help="Valor para busca")
    parser.add_argument("--limit", type=int, default=10, help="Limite de resultados")
    parser.add_argument("--details", type=str, help="Mostrar detalhes de uma análise específica")
    parser.add_argument("--export", type=str, help="Exportar análises para arquivo JSON")
    
    args = parser.parse_args()
    
    if args.stats:
        success = show_stats()
    elif args.search and args.value:
        success = search_analyses(args.search, args.value, args.limit)
    elif args.details:
        success = show_analysis_details(args.details)
    elif args.export:
        success = export_analyses(args.export, args.limit)
    else:
        print("❌ Especifique uma ação: --stats, --search, --details ou --export")
        print("💡 Use --help para ver todas as opções")
        success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
