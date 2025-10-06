#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processador em lote para analisar TODAS as imagens pendentes do MongoDB
"""
import sys
import os
import time
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

def process_all_pending_images(limit=None, dry_run=False, force=False):
    """Processar todas as imagens pendentes do MongoDB"""
    print("🖼️ Processador em Lote - Todas as Imagens Pendentes")
    print("=" * 60)
    
    if force:
        print("⚡ MODO FORCE ativado - reprocessando TODAS as imagens")
        print("⚠️  Ignorando status de processamento anterior")
    
    try:
        from src.services.database_service import DatabaseService
        from src.services.image_service_simple import ImageServiceSimple
        from src.services.download_service import DownloadService
        
        # Inicializar serviços
        print("🔧 Inicializando serviços...")
        db_service = DatabaseService()
        image_service = ImageServiceSimple()
        download_service = DownloadService()
        
        # Obter estatísticas
        print("📊 Verificando imagens pendentes...")
        stats = db_service.get_conversation_stats()
        
        print(f"   📋 Total de conversas: {stats.get('total_conversations', 0)}")
        print(f"   🖼️ Conversas com imagens: {stats.get('image_conversations', 0)}")
        print(f"   ⏳ Conversas pendentes: {stats.get('pending_conversations', 0)}")
        
        # Buscar conversas pendentes
        if force:
            print("\n🔍 Buscando TODAS as conversas com imagens (modo force)...")
            # Buscar todas as conversas com imagens, ignorando status
            query = {
                "$or": [
                    {"image_messages": {"$gt": 0}},
                    {"media_messages": {"$gt": 0}},
                    {"contacts.messages.type": "image"},
                    {"contacts.messages.media_type": "image"}
                ]
            }
            pending_conversations = list(db_service.db.diarios.find(query).limit(limit or 100))
        else:
            print("\n🔍 Buscando conversas com imagens pendentes...")
            pending_conversations = db_service.get_conversations_with_pending_images(limit=limit or 100)
        
        if not pending_conversations:
            print("✅ Nenhuma imagem pendente encontrada!")
            print("💡 Todas as imagens já foram analisadas.")
            return True
        
        print(f"📋 Encontradas {len(pending_conversations)} conversas pendentes")
        
        if dry_run:
            print("\n🧪 MODO DRY-RUN - Apenas listando imagens pendentes:")
            print("-" * 60)
            
            total_pending_images = 0
            for i, conversation in enumerate(pending_conversations, 1):
                conv_id = conversation['_id']
                user_name = conversation.get('user_name', 'Desconhecido')
                
                # Converter ObjectId para string
                conv_id_str = str(conv_id)
                
                # Buscar imagens pendentes desta conversa
                if force:
                    pending_images = db_service.get_all_images_for_conversation(conv_id_str)
                else:
                    pending_images = db_service.get_pending_images_for_conversation(conv_id_str)
                
                print(f"{i:2d}. {conv_id_str[:8]} - {user_name[:30]:<30} ({len(pending_images)} imagens)")
                total_pending_images += len(pending_images)
            
            print("-" * 60)
            print(f"📊 Total de imagens pendentes: {total_pending_images}")
            print("💡 Execute sem --dry-run para processar")
            return True
        
        # Processar conversas
        print(f"\n🚀 Iniciando processamento de {len(pending_conversations)} conversas...")
        print("=" * 60)
        print("💡 O processamento mostrará:")
        print("   📥 Download de cada arquivo")
        print("   🖼️ Análise com LLaVA")
        print("   📝 Preview da descrição")
        print("   💾 Salvamento no MongoDB")
        print("   ⏱️ Tempos de cada etapa")
        print("=" * 60)
        
        total_processed = 0
        total_successful = 0
        total_failed = 0
        start_time = time.time()
        
        for i, conversation in enumerate(pending_conversations, 1):
            conv_id = conversation['_id']
            user_name = conversation.get('user_name', 'Desconhecido')
            
            # Converter ObjectId para string se necessário
            conv_id_str = str(conv_id)
            print(f"\n📁 [{i}/{len(pending_conversations)}] Processando: {conv_id_str[:8]} - {user_name}")
            print("-" * 50)
            
            try:
                # Buscar imagens desta conversa
                if force:
                    # No modo force, buscar TODAS as imagens, não apenas pendentes
                    pending_images = db_service.get_all_images_for_conversation(conv_id_str)
                else:
                    # Modo normal, buscar apenas imagens pendentes
                    pending_images = db_service.get_pending_images_for_conversation(conv_id_str)
                
                if not pending_images:
                    if force:
                        print("   ✅ Nenhuma imagem encontrada nesta conversa")
                    else:
                        print("   ✅ Nenhuma imagem pendente nesta conversa")
                    continue
                
                if force:
                    print(f"   🖼️ Encontradas {len(pending_images)} imagens (reprocessando todas)")
                else:
                    print(f"   🖼️ Encontradas {len(pending_images)} imagens pendentes")
                
                # Processar cada imagem
                conv_successful = 0
                conv_failed = 0
                
                for j, image_msg in enumerate(pending_images, 1):
                    message_id = image_msg['message_id']
                    contact_name = image_msg.get('contact_name', 'Desconhecido')
                    
                    print(f"   [{j}/{len(pending_images)}] 🖼️ Imagem: {message_id[:8]} - {contact_name[:20]}")
                    
                    # Processar imagem usando o método do ImageService
                    result = process_image_message(
                        image_msg, 
                        download_service, 
                        db_service, 
                        image_service,
                        show_progress=True
                    )
                    
                    if result['success']:
                        conv_successful += 1
                    else:
                        conv_failed += 1
                
                print(f"   📊 Resultado: {conv_successful} sucessos, {conv_failed} falhas")
                
                total_processed += len(pending_images)
                total_successful += conv_successful
                total_failed += conv_failed
                
            except Exception as e:
                print(f"   ❌ Erro ao processar conversa: {e}")
                continue
        
        # Resumo final
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("🎉 PROCESSAMENTO CONCLUÍDO!")
        print("=" * 60)
        print(f"⏱️  Tempo total: {elapsed_time:.1f}s")
        print(f"📊 Conversas processadas: {len(pending_conversations)}")
        print(f"🖼️ Imagens processadas: {total_processed}")
        print(f"✅ Sucessos: {total_successful}")
        print(f"❌ Falhas: {total_failed}")
        print(f"📈 Taxa de sucesso: {(total_successful/total_processed*100):.1f}%" if total_processed > 0 else "N/A")
        
        # Limpeza
        image_service.close()
        download_service.close()
        db_service.close()
        
        return total_failed == 0
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

def process_image_message(image_msg, download_service, db_service, image_service, show_progress=False):
    """Processar uma mensagem de imagem individual"""
    try:
        message_id = image_msg['message_id']
        file_url = image_msg.get('file_url', '')
        contact_name = image_msg.get('contact_name', 'Desconhecido')
        
        if show_progress:
            print(f"      📥 Baixando de: {file_url[:50]}...")
        
        # 1. Baixar arquivo
        download_start = time.time()
        image_path = download_service.download_media_file(
            image_msg['conversation_id'],
            str(image_msg['message_id']),
            file_url,
            media_type='image'
        )
        download_time = time.time() - download_start
        
        if not image_path:
            if show_progress:
                print(f"      ❌ Falha no download após {download_time:.1f}s")
            return {'success': False, 'error': 'Download failed'}
        
        # Verificar tamanho do arquivo
        file_size = Path(image_path).stat().st_size
        if show_progress:
            print(f"      ✅ Download concluído ({file_size/1024:.1f}KB em {download_time:.1f}s)")
        
        # 2. Analisar imagem
        if show_progress:
            print(f"      🖼️ Iniciando análise...")
        analysis_start = time.time()
        
        # Usar sistema de múltiplos prompts automático
        result = image_service.analyze_image(image_path)
        analysis_time = time.time() - analysis_start
        
        if not result:
            if show_progress:
                print(f"      ❌ Falha na análise após {analysis_time:.1f}s")
            return {'success': False, 'error': 'Analysis failed'}
        
        # Mostrar preview da análise
        description_preview = result['description'][:100] + "..." if len(result['description']) > 100 else result['description']
        if show_progress:
            print(f"      ✅ Análise concluída em {analysis_time:.1f}s")
            print(f"      📝 Preview: {description_preview}")
            print(f"      📊 Modelo: {result['model']}")
            if 'prompt_name' in result:
                print(f"      🎯 Prompt usado: {result['prompt_name']}")
        
        # 3. Salvar JSON (mesmo padrão das transcrições)
        if show_progress:
            print(f"      💾 Salvando JSON...")
        json_start = time.time()
        
        # Preparar dados para JSON
        json_data = {
            "conversation_id": image_msg['conversation_id'],
            "message_id": str(image_msg['message_id']),
            "image_analysis": {
                "description": result['description'],
                "prompt_used": result['prompt_used'],
                "generation_time": result['generation_time'],
                "model": result['model'],
                "analysis_time": analysis_time,
                "file_size": file_size,
                "download_time": download_time
            },
            "created_at": datetime.now().isoformat(),
            "model": result['model'],
            "device": "ollama"
        }
        
        # Salvar JSON usando o método do ImageService
        json_path = image_service.save_analysis_to_json(
            image_msg['conversation_id'],
            str(image_msg['message_id']),
            json_data['image_analysis']
        )
        json_time = time.time() - json_start
        
        if not json_path:
            if show_progress:
                print(f"      ❌ Falha ao salvar JSON após {json_time:.1f}s")
            return {'success': False, 'error': 'JSON save failed'}
        
        if show_progress:
            print(f"      ✅ JSON salvo em {json_time:.1f}s: {Path(json_path).name}")
        
        # 4. Salvar no diário (MongoDB)
        if show_progress:
            print(f"      💾 Salvando no diário...")
        diary_start = time.time()
        
        # Preparar dados da análise para o diário
        analysis_data = {
            'description': result['description'],
            'prompt_used': result['prompt_used'],
            'generation_time': result['generation_time'],
            'model': result['model'],
            'analysis_time': analysis_time,
            'file_size': file_size,
            'download_time': download_time
        }
        
        diary_success = db_service.update_image_analysis(
            image_msg['conversation_id'],
            image_msg['contact_idx'],
            image_msg['message_idx'],
            analysis_data
        )
        diary_time = time.time() - diary_start
        
        if not diary_success:
            if show_progress:
                print(f"      ❌ Falha ao salvar no diário após {diary_time:.1f}s")
            return {'success': False, 'error': 'Diary save failed'}
        
        if show_progress:
            print(f"      ✅ Diário atualizado em {diary_time:.1f}s")
        
        # 5. Salvar na collection de análises
        if show_progress:
            print(f"      💾 Salvando na collection de análises...")
        collection_start = time.time()
        
        # Preparar dados para a collection
        collection_data = {
            "mensagem_id": str(image_msg['message_id']),
            "conversation_id": image_msg['conversation_id'],
            "contact_name": image_msg.get('contact_name', 'Desconhecido'),
            "image_analysis": analysis_data,
            "image_description": result['description'],
            "model": result['model'],
            "device": "ollama",
            "file_size": file_size,
            "generation_time": result['generation_time']
        }
        
        collection_success = db_service.save_image_analysis_to_collection(collection_data)
        collection_time = time.time() - collection_start
        
        if not collection_success:
            if show_progress:
                print(f"      ❌ Falha ao salvar na collection após {collection_time:.1f}s")
            return {'success': False, 'error': 'Collection save failed'}
        
        if show_progress:
            print(f"      ✅ Collection atualizada em {collection_time:.1f}s ({len(result['description'])} chars)")
        
        return {'success': True, 'analysis': result}
        
    except Exception as e:
        if show_progress:
            print(f"      ❌ Erro: {e}")
        return {'success': False, 'error': str(e)}

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Processar todas as imagens pendentes")
    parser.add_argument("--limit", type=int, help="Limite de conversas para processar")
    parser.add_argument("--dry-run", action="store_true", help="Apenas listar imagens pendentes")
    parser.add_argument("--force", action="store_true", help="Reprocessar TODAS as imagens, ignorando status")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🧪 MODO DRY-RUN ativado - nenhum processamento será feito")
    
    if args.force:
        print("⚡ MODO FORCE ativado - reprocessando TODAS as imagens")
    
    if args.limit:
        print(f"📊 Limite de conversas: {args.limit}")
    
    print()
    
    success = process_all_pending_images(
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force
    )
    
    if success:
        print("\n✅ Processamento concluído com sucesso!")
        return 0
    else:
        print("\n❌ Processamento concluído com erros")
        return 1

if __name__ == "__main__":
    sys.exit(main())
