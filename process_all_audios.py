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

def process_all_pending_audios(limit=None, dry_run=False):
    """Processar todos os áudios pendentes do MongoDB"""
    print("🎙️ Processador em Lote - Todos os Áudios Pendentes")
    print("=" * 60)
    
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
                
                # Buscar áudios pendentes desta conversa
                pending_audios = db_service.get_pending_audios_for_conversation(str(conv_id))
                
                print(f"{i:2d}. {conv_id[:8]} - {user_name[:30]:<30} ({len(pending_audios)} áudios)")
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
            
            print(f"\n📁 [{i}/{len(pending_conversations)}] Processando: {conv_id[:8]} - {user_name}")
            print("-" * 50)
            
            try:
                # Buscar áudios pendentes desta conversa
                pending_audios = db_service.get_pending_audios_for_conversation(str(conv_id))
                
                if not pending_audios:
                    print("   ✅ Nenhum áudio pendente nesta conversa")
                    continue
                
                print(f"   🎵 Encontrados {len(pending_audios)} áudios pendentes")
                
                # Processar cada áudio
                conv_successful = 0
                conv_failed = 0
                
                for j, audio_msg in enumerate(pending_audios, 1):
                    message_id = audio_msg['message_id']
                    file_url = audio_msg.get('file_url', '')
                    contact_name = audio_msg.get('contact_name', 'Desconhecido')
                    
                    print(f"   [{j}/{len(pending_audios)}] 🎵 Áudio: {message_id[:8]} - {contact_name[:20]}")
                    print(f"      📥 Baixando de: {file_url[:50]}...")
                    
                    try:
                        # 1. Baixar arquivo
                        download_start = time.time()
                        audio_path = download_service.download_audio_file(
                            audio_msg['conversation_id'],
                            str(audio_msg['message_id']),
                            audio_msg['file_url']
                        )
                        download_time = time.time() - download_start
                        
                        if not audio_path:
                            print(f"      ❌ Falha no download após {download_time:.1f}s")
                            conv_failed += 1
                            continue
                        
                        # Verificar tamanho do arquivo
                        file_size = Path(audio_path).stat().st_size
                        print(f"      ✅ Download concluído ({file_size/1024:.1f}KB em {download_time:.1f}s)")
                        
                        # 2. Transcrever
                        print(f"      🎙️ Iniciando transcrição...")
                        transcription_start = time.time()
                        result = audio_service.transcribe_file(audio_path)
                        transcription_time = time.time() - transcription_start
                        
                        if not result:
                            print(f"      ❌ Falha na transcrição após {transcription_time:.1f}s")
                            conv_failed += 1
                            continue
                        
                        # Mostrar preview da transcrição
                        text_preview = result['text'][:100] + "..." if len(result['text']) > 100 else result['text']
                        print(f"      ✅ Transcrição concluída em {transcription_time:.1f}s")
                        print(f"      📝 Preview: {text_preview}")
                        print(f"      📊 Confiança: {result['confidence']:.2f}, Duração: {result['duration']:.1f}s")
                        
                        # 3. Salvar no MongoDB
                        print(f"      💾 Salvando no MongoDB...")
                        save_start = time.time()
                        
                        # Preparar dados da transcrição
                        transcription_data = {
                            'text': result['text'],
                            'confidence': result['confidence'],
                            'duration': result['duration'],
                            'language': result.get('language'),
                            'transcription_time': transcription_time,
                            'file_size': file_size,
                            'download_time': download_time
                        }
                        
                        success = db_service.update_audio_transcription(
                            audio_msg['conversation_id'],
                            audio_msg['contact_idx'],
                            audio_msg['message_idx'],
                            transcription_data
                        )
                        save_time = time.time() - save_start
                        
                        if success:
                            print(f"      ✅ Salvo no MongoDB em {save_time:.1f}s ({len(result['text'])} chars)")
                            conv_successful += 1
                        else:
                            print(f"      ❌ Falha ao salvar no MongoDB após {save_time:.1f}s")
                            conv_failed += 1
                        
                    except Exception as e:
                        print(f"      ❌ Erro: {e}")
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
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🧪 MODO DRY-RUN ativado - nenhum processamento será feito")
    
    if args.limit:
        print(f"📊 Limite de conversas: {args.limit}")
    
    print()
    
    success = process_all_pending_audios(
        limit=args.limit,
        dry_run=args.dry_run
    )
    
    if success:
        print("\n✅ Processamento concluído com sucesso!")
        return 0
    else:
        print("\n❌ Processamento concluído com erros")
        return 1

if __name__ == "__main__":
    sys.exit(main())
