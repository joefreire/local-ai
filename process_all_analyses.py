#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processador em lote para analisar TODOS os diários com novo fluxo v2
Análise por contato individual + resumo global do diário
"""
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
import argparse

# Configurar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

def process_all_diaries_analysis_v2(limit=None, dry_run=False, force=False, contact_filter=None, show_progress=True):
    """Processar todos os diários para análise v2"""
    print("🧠 Processador em Lote v2 - Análise por Contato + Resumo Global")
    print("=" * 70)
    
    if force:
        print("⚡ MODO FORCE ativado - reprocessando TODOS os diários")
        print("⚠️  Ignorando status de análise anterior")
    
    if contact_filter:
        print(f"🎯 FILTRO DE CONTATO ativado - apenas: {contact_filter}")
    
    try:
        from src.services.database_service import DatabaseService
        from src.services.analysis_service import LlamaService
        
        # Inicializar serviços
        print("🔧 Inicializando serviços...")
        db_service = DatabaseService()
        analysis_service = LlamaService()
        
        # Testar conexão com Ollama
        print("🔍 Verificando conexão com Ollama...")
        connection_result = analysis_service.test_connection()
        if not connection_result['connected']:
            print(f"❌ Ollama não disponível: {connection_result.get('error', 'Erro desconhecido')}")
            return False
        
        print(f"✅ Ollama conectado - Modelo: {connection_result['selected_model']}")
        
        # Obter estatísticas
        print("📊 Verificando diários...")
        stats = db_service.get_diary_analysis_stats_v2()
        
        print(f"   📋 Total de diários: {stats.get('total_diaries', 0)}")
        print(f"   ✅ Diários analisados v2: {stats.get('analyzed_diaries', 0)}")
        print(f"   ⏳ Diários pendentes: {stats.get('pending_diaries', 0)}")
        print(f"   📈 Taxa de análise: {stats.get('analysis_rate', 0):.1f}%")
        
        # Buscar diários
        if force:
            print("\n🔍 Buscando TODOS os diários (modo force)...")
            # Buscar todos os diários, ignorando status de análise
            query = {}
            all_diaries = list(db_service.db.diarios.find(query).limit(limit or 1000))
        else:
            print("\n🔍 Buscando diários sem análise v2...")
            # Buscar diários que ainda não foram analisados com v2
            all_diaries = db_service.get_diaries_without_analysis_v2(limit=limit or 1000)
        
        if not all_diaries:
            print("✅ Nenhum diário pendente de análise v2 encontrado!")
            print("💡 Todos os diários já foram analisados com a versão 2.")
            return True
        
        print(f"📋 Encontradas {len(all_diaries)} diários para análise v2")
        
        # Filtrar por contato se especificado
        if contact_filter:
            filtered_diaries = []
            for diary in all_diaries:
                contacts = diary.get('contacts', [])
                for contact in contacts:
                    contact_name = contact.get('contact_name', '')
                    if contact_filter.lower() in contact_name.lower():
                        filtered_diaries.append(diary)
                        break
            
            all_diaries = filtered_diaries
            print(f"🎯 Após filtro de contato: {len(all_diaries)} diários")
            
            if not all_diaries:
                print("❌ Nenhum diário encontrado com o contato especificado")
                return True
        
        if dry_run:
            print("\n🧪 MODO DRY-RUN - Apenas listando diários:")
            print("-" * 70)
            
            for i, diary in enumerate(all_diaries, 1):
                diary_id = diary['_id']
                user_name = diary.get('user_name', 'Desconhecido')
                date = diary.get('date_formatted', 'Data não disponível')
                contacts_count = len(diary.get('contacts', []))
                
                # Verificar se já tem análise v2
                has_analysis_v2 = bool(diary.get('contact_analyses')) and diary.get('analysis_version') == 'v2'
                analysis_status = "✅ Analisado v2" if has_analysis_v2 else "⏳ Pendente"
                
                print(f"{i:2d}. {str(diary_id)[:8]} - {user_name[:25]:<25} | {contacts_count} contatos | {analysis_status}")
                
                # Mostrar contatos se filtro especificado
                if contact_filter:
                    for contact in diary.get('contacts', []):
                        contact_name = contact.get('contact_name', 'Desconhecido')
                        if contact_filter.lower() in contact_name.lower():
                            messages_count = len(contact.get('messages', []))
                            print(f"    🎯 {contact_name} ({messages_count} mensagens)")
            
            print("-" * 70)
            print(f"📊 Total de diários: {len(all_diaries)}")
            print("💡 Execute sem --dry-run para processar")
            return True
        
        # Criar diretório de resultados
        results_dir = Path("analyses_results_v2")
        results_dir.mkdir(exist_ok=True)
        
        # Processar diários
        print(f"\n🚀 Iniciando análise v2 de {len(all_diaries)} diários...")
        print("=" * 70)
        print("💡 O processamento mostrará:")
        print("   📋 Busca de dados do diário")
        print("   📅 Contexto histórico (últimos 7 dias)")
        print("   👥 Análise individual de cada contato")
        print("   📊 Resumo global do diário")
        print("   📝 Preview dos resultados")
        print("   💾 Salvamento no MongoDB e JSON")
        print("   ⏱️ Tempos de cada etapa")
        print("=" * 70)
        
        total_processed = 0
        total_successful = 0
        total_failed = 0
        start_time = time.time()
        
        for i, diary in enumerate(all_diaries, 1):
            diary_id = diary['_id']
            user_name = diary.get('user_name', 'Desconhecido')
            
            # Converter ObjectId para string
            diary_id_str = str(diary_id)
            print(f"\n📁 [{i}/{len(all_diaries)}] Analisando: {diary_id_str[:8]} - {user_name}")
            print("-" * 60)
            
            try:
                # Buscar dados do diário
                if show_progress:
                    print(f"   📋 Buscando dados do diário...")
                data_start = time.time()
                
                diary_data = db_service.get_diary_text_for_analysis_v2(diary_id_str)
                data_time = time.time() - data_start
                
                if not diary_data:
                    print(f"   ❌ Erro ao buscar dados do diário após {data_time:.1f}s")
                    total_failed += 1
                    continue
                
                contacts_count = len(diary_data.get('contacts', []))
                historical_count = len(diary_data.get('historical_context', []))
                print(f"   ✅ Dados obtidos em {data_time:.1f}s: {contacts_count} contatos, {historical_count} mensagens históricas")
                
                # Executar análise v2
                if show_progress:
                    print(f"   🧠 Executando análise v2 (contatos + resumo global)...")
                analysis_start = time.time()
                
                analysis = analysis_service.analyze_diary(diary_data)
                analysis_time = time.time() - analysis_start
                
                if 'error' in analysis:
                    print(f"   ❌ Erro na análise após {analysis_time:.1f}s: {analysis['error']}")
                    total_failed += 1
                    continue
                
                # Mostrar preview dos resultados
                contact_analyses = analysis.get('contact_analyses', [])
                diary_summary = analysis.get('diary_summary', {})
                
                print(f"   ✅ Análise v2 concluída em {analysis_time:.1f}s")
                print(f"   👥 Contatos analisados: {len(contact_analyses)}")
                
                # Mostrar preview do resumo global
                if isinstance(diary_summary, dict):
                    summary_text = diary_summary.get('result', 'Resumo não disponível')
                else:
                    summary_text = diary_summary
                
                summary_preview = summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
                print(f"   📊 Resumo global: {summary_preview}")
                
                # Mostrar preview de alguns contatos
                for j, contact_analysis in enumerate(contact_analyses[:2]):  # Mostrar apenas os 2 primeiros
                    contact_name = contact_analysis.get('contact_name', 'Desconhecido')
                    contact_summary = contact_analysis.get('summary', {}).get('result', 'Sem resumo')
                    contact_preview = contact_summary[:80] + "..." if len(contact_summary) > 80 else contact_summary
                    print(f"   👤 {contact_name}: {contact_preview}")
                
                if len(contact_analyses) > 2:
                    print(f"   ... e mais {len(contact_analyses) - 2} contatos")
                
                # Criar resultado completo
                if show_progress:
                    print(f"   📊 Criando resultado completo...")
                result_start = time.time()
                
                result = create_analysis_result_v2(diary_id_str, diary_data, analysis, contact_filter)
                result_time = time.time() - result_start
                
                # Salvar JSON
                if show_progress:
                    print(f"   💾 Salvando JSON...")
                json_start = time.time()
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if contact_filter:
                    filename = f"analysis_v2_{diary_id_str[:8]}_{contact_filter}_{timestamp}.json"
                else:
                    filename = f"analysis_v2_{diary_id_str[:8]}_complete_{timestamp}.json"
                
                filepath = results_dir / filename
                
                # Função para converter datetime para string
                def json_serial(obj):
                    if hasattr(obj, 'isoformat'):
                        return obj.isoformat()
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=json_serial)
                
                json_time = time.time() - json_start
                print(f"   ✅ JSON salvo em {json_time:.1f}s: {filename}")
                
                # Salvar no banco de dados
                if show_progress:
                    print(f"   💾 Salvando no MongoDB...")
                db_start = time.time()
                
                success = db_service.save_diary_analysis_v2(diary_id_str, analysis)
                db_time = time.time() - db_start
                
                if success:
                    print(f"   ✅ MongoDB atualizado em {db_time:.1f}s")
                    total_successful += 1
                else:
                    print(f"   ❌ Erro ao salvar no MongoDB após {db_time:.1f}s")
                    total_failed += 1
                
                total_processed += 1
                
            except Exception as e:
                print(f"   ❌ Erro ao analisar diário: {e}")
                total_failed += 1
                continue
        
        # Resumo final
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 70)
        print("🎉 ANÁLISE V2 CONCLUÍDA!")
        print("=" * 70)
        print(f"⏱️  Tempo total: {elapsed_time:.1f}s")
        print(f"📊 Diários processados: {total_processed}")
        print(f"✅ Sucessos: {total_successful}")
        print(f"❌ Falhas: {total_failed}")
        print(f"📈 Taxa de sucesso: {(total_successful/total_processed*100):.1f}%" if total_processed > 0 else "N/A")
        print(f"📁 Resultados salvos em: {results_dir}")
        
        # Limpeza
        analysis_service.close()
        db_service.close()
        
        return total_failed == 0
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_analysis_result_v2(diary_id: str, diary_data: dict, analysis: dict, contact_name: str = None):
    """Criar resultado completo da análise v2"""
    
    # Informações básicas
    result = {
        "analysis_info": {
            "diary_id": diary_id,
            "analysis_date": datetime.now().isoformat(),
            "analysis_version": "v2",
            "scope": f"contato_{contact_name}" if contact_name else "diario_completo",
            "model_used": "llama3.2:3b"
        },
        "diary_info": {
            "user_name": diary_data.get('user_name', 'Desconhecido'),
            "company_name": diary_data.get('company_name', 'Desconhecida'),
            "date": diary_data.get('date', 'Data não disponível'),
            "date_formatted": diary_data.get('date_formatted', 'Data não disponível'),
            "total_contacts": len(diary_data.get('contacts', [])),
            "analyzed_contact": contact_name if contact_name else "Todos os contatos"
        },
        "analysis": analysis,
        "raw_data": diary_data
    }
    
    # Adicionar estatísticas detalhadas
    contacts = diary_data.get('contacts', [])
    total_messages = 0
    total_audio_messages = 0
    total_image_messages = 0
    audio_transcribed = 0
    image_analyzed = 0
    
    contact_details = []
    for contact in contacts:
        messages = contact.get('messages', [])
        contact_total = len(messages)
        contact_audio = 0
        contact_image = 0
        contact_audio_transcribed = 0
        contact_image_analyzed = 0
        
        for message in messages:
            message_type = message.get('message_type', 'text')
            if message_type in ['audio', 'audio_transcribed']:
                contact_audio += 1
                if message.get('has_transcription'):
                    contact_audio_transcribed += 1
            elif message_type in ['image', 'image_analyzed']:
                contact_image += 1
                if message.get('has_image_analysis'):
                    contact_image_analyzed += 1
        
        total_messages += contact_total
        total_audio_messages += contact_audio
        total_image_messages += contact_image
        audio_transcribed += contact_audio_transcribed
        image_analyzed += contact_image_analyzed
        
        contact_details.append({
            "contact_name": contact.get('contact_name', 'Desconhecido'),
            "total_messages": contact_total,
            "audio_messages": contact_audio,
            "image_messages": contact_image,
            "audio_transcribed": contact_audio_transcribed,
            "image_analyzed": contact_image_analyzed,
            "text_messages": contact_total - contact_audio - contact_image
        })
    
    # Contexto histórico
    historical_context = diary_data.get('historical_context', [])
    
    result["detailed_stats"] = {
        "total_messages": total_messages,
        "total_audio_messages": total_audio_messages,
        "total_image_messages": total_image_messages,
        "audio_transcribed": audio_transcribed,
        "image_analyzed": image_analyzed,
        "text_messages": total_messages - total_audio_messages - total_image_messages,
        "historical_messages": len(historical_context),
        "contacts_breakdown": contact_details
    }
    
    return result

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Processar todos os diários para análise v2")
    parser.add_argument("--limit", type=int, help="Limite de diários para analisar")
    parser.add_argument("--dry-run", action="store_true", help="Apenas listar diários")
    parser.add_argument("--force", action="store_true", help="Reprocessar TODOS os diários, ignorando status")
    parser.add_argument("--contact", type=str, help="Filtrar por nome de contato específico")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🧪 MODO DRY-RUN ativado - nenhuma análise será feita")
    
    if args.force:
        print("⚡ MODO FORCE ativado - reprocessando TODOS os diários")
    
    if args.limit:
        print(f"📊 Limite de diários: {args.limit}")
    
    if args.contact:
        print(f"🎯 Filtro de contato: {args.contact}")
    
    print()
    
    success = process_all_diaries_analysis_v2(
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force,
        contact_filter=args.contact
    )
    
    if success:
        print("\n✅ Análise v2 concluída com sucesso!")
        return 0
    else:
        print("\n❌ Análise v2 concluída com erros")
        return 1

if __name__ == "__main__":
    sys.exit(main())
