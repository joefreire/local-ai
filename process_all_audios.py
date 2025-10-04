#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processador em lote para transcrever TODOS os áudios pendentes do MongoDB
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

def process_all_pending_audios(limit=None, dry_run=False, force=False):
    """Processar todos os áudios pendentes do MongoDB"""
    print("🎙️ Processador em Lote - Todos os Áudios Pendentes")
    print("=" * 60)
    
    if force:
        print("⚡ MODO FORCE ativado - reprocessando TODOS os áudios")
        print("⚠️  Ignorando status de processamento anterior")
    
    try:
        from src.services.database_service import DatabaseService
        from src.services.audio_service import AudioService
        from src.services.download_service import DownloadService
        
        # Inicializar serviços
        print("🔧 Inicializando serviços...")
        db_service = DatabaseService()
        audio_service = AudioService()
        download_service = DownloadService()
        
        # Obter estatísticas
        print("📊 Verificando áudios pendentes...")
        stats = db_service.get_conversation_stats()
        
        print(f"   📋 Total de conversas: {stats.get('total_conversations', 0)}")
        print(f"   🎵 Conversas com áudio: {stats.get('audio_conversations', 0)}")
        print(f"   ⏳ Conversas pendentes: {stats.get('pending_conversations', 0)}")
        
        # Buscar conversas pendentes
        if force:
            print("\n🔍 Buscando TODAS as conversas com áudios (modo force)...")
            # Buscar todas as conversas com áudios, ignorando status
            query = {
                "$or": [
                    {"audio_messages": {"$gt": 0}},
                    {"media_messages": {"$gt": 0}},
                    {"contacts.messages.type": "audio"},
                    {"contacts.messages.media_type": "audio"}
                ]
            }
            pending_conversations = list(db_service.db.diarios.find(query).limit(limit or 100))
        else:
            print("\n🔍 Buscando conversas com áudios pendentes...")
            pending_conversations = db_service.get_conversations_with_pending_audios(limit=limit or 100)
        
        if not pending_conversations:
            print("✅ Nenhum áudio pendente encontrado!")
            print("💡 Todos os áudios já foram transcritos.")
            return True
        
        print(f"📋 Encontradas {len(pending_conversations)} conversas pendentes")
        
        if dry_run:
            print("\n🧪 MODO DRY-RUN - Apenas listando áudios pendentes:")
            print("-" * 60)
            
            total_pending_audios = 0
            for i, conversation in enumerate(pending_conversations, 1):
                conv_id = conversation['_id']
                user_name = conversation.get('user_name', 'Desconhecido')
                
                # Converter ObjectId para string
                conv_id_str = str(conv_id)
                
                # Buscar áudios pendentes desta conversa
                if force:
                    pending_audios = db_service.get_all_audios_for_conversation(conv_id_str)
                else:
                    pending_audios = db_service.get_pending_audios_for_conversation(conv_id_str)
                
                print(f"{i:2d}. {conv_id_str[:8]} - {user_name[:30]:<30} ({len(pending_audios)} áudios)")
                total_pending_audios += len(pending_audios)
            
            print("-" * 60)
            print(f"📊 Total de áudios pendentes: {total_pending_audios}")
            print("💡 Execute sem --dry-run para processar")
            return True
        
        # Processar conversas
        print(f"\n🚀 Iniciando processamento de {len(pending_conversations)} conversas...")
        print("=" * 60)
        print("💡 O processamento mostrará:")
        print("   📥 Download de cada arquivo")
        print("   🎙️ Transcrição com Whisper")
        print("   📝 Preview do texto transcrito")
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
                # Buscar áudios desta conversa
                if force:
                    # No modo force, buscar TODOS os áudios, não apenas pendentes
                    pending_audios = db_service.get_all_audios_for_conversation(conv_id_str)
                else:
                    # Modo normal, buscar apenas áudios pendentes
                    pending_audios = db_service.get_pending_audios_for_conversation(conv_id_str)
                
                if not pending_audios:
                    if force:
                        print("   ✅ Nenhum áudio encontrado nesta conversa")
                    else:
                        print("   ✅ Nenhum áudio pendente nesta conversa")
                    continue
                
                if force:
                    print(f"   🎵 Encontrados {len(pending_audios)} áudios (reprocessando todos)")
                else:
                    print(f"   🎵 Encontrados {len(pending_audios)} áudios pendentes")
                
                # Processar cada áudio
                conv_successful = 0
                conv_failed = 0
                
                for j, audio_msg in enumerate(pending_audios, 1):
                    message_id = audio_msg['message_id']
                    contact_name = audio_msg.get('contact_name', 'Desconhecido')
                    
                    print(f"   [{j}/{len(pending_audios)}] 🎵 Áudio: {message_id[:8]} - {contact_name[:20]}")
                    
                    # Processar áudio usando o método do AudioService
                    result = audio_service.process_audio_message(
                        audio_msg, 
                        download_service, 
                        db_service, 
                        show_progress=True
                    )
                    
                    if result['success']:
                        conv_successful += 1
                    else:
                        conv_failed += 1
                
                print(f"   📊 Resultado: {conv_successful} sucessos, {conv_failed} falhas")
                
                total_processed += len(pending_audios)
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
        print(f"🎵 Áudios processados: {total_processed}")
        print(f"✅ Sucessos: {total_successful}")
        print(f"❌ Falhas: {total_failed}")
        print(f"📈 Taxa de sucesso: {(total_successful/total_processed*100):.1f}%" if total_processed > 0 else "N/A")
        
        # Limpeza
        audio_service.close()
        download_service.close()
        db_service.close()
        
        return total_failed == 0
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Processar todos os áudios pendentes")
    parser.add_argument("--limit", type=int, help="Limite de conversas para processar")
    parser.add_argument("--dry-run", action="store_true", help="Apenas listar áudios pendentes")
    parser.add_argument("--force", action="store_true", help="Reprocessar TODOS os áudios, ignorando status")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🧪 MODO DRY-RUN ativado - nenhum processamento será feito")
    
    if args.force:
        print("⚡ MODO FORCE ativado - reprocessando TODOS os áudios")
    
    if args.limit:
        print(f"📊 Limite de conversas: {args.limit}")
    
    print()
    
    success = process_all_pending_audios(
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
