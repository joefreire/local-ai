#!/usr/bin/env python3
"""
Teste real de transcrição usando primeiro arquivo pendente
"""
import sys
from pathlib import Path
import time

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

def teste_real_transcricao():
    """Teste real de transcrição com primeiro arquivo pendente"""
    print("Teste Real de Transcrição")
    print("=" * 50)
    
    try:
        from src.services.database_service import DatabaseService
        from src.services.audio_service import AudioService
        
        print("1. Conectando ao banco de dados...")
        db_service = DatabaseService()
        stats = db_service.get_conversation_stats()
        
        print(f"   Total de diários: {stats.get('total_conversations', 0)}")
        print(f"   Diários com áudio: {stats.get('audio_conversations', 0)}")
        print(f"   Diários pendentes: {stats.get('pending_conversations', 0)}")
        
        print("\n2. Buscando conversas com áudios pendentes...")
        pending_conversations = db_service.get_conversations_with_pending_audios(limit=10)
        
        if not pending_conversations:
            print("   Nenhuma conversa com áudio pendente encontrada")
            print("   Verifique se há dados no MongoDB")
            return
        
        print(f"   Encontradas {len(pending_conversations)} conversas pendentes")
        
        # Buscar primeira conversa com áudio pendente real
        audio_msg = None
        for conversation in pending_conversations:
            conv_id = conversation['_id']
            print(f"   Verificando conversa: {conv_id}")
            
            pending_audios = db_service.get_pending_audios_for_conversation(str(conv_id))
            
            if pending_audios:
                print(f"   Encontrados {len(pending_audios)} áudios pendentes nesta conversa")
                audio_msg = pending_audios[0]
                break
            else:
                print("   Nenhum áudio pendente nesta conversa")
        
        if not audio_msg:
            print("   Nenhum áudio pendente encontrado em nenhuma conversa")
            return
        print(f"   Áudio encontrado:")
        print(f"      - ID: {audio_msg['message_id']}")
        print(f"      - URL: {audio_msg.get('file_url', 'N/A')[:50]}...")
        print(f"      - Contato: {audio_msg.get('contact_name', 'N/A')}")
        print(f"      - Criado em: {audio_msg.get('created_at', 'N/A')}")
        
        print("\n3. Verificando GPU...")
        audio_service = AudioService()
        gpu_info = audio_service.get_gpu_info()
        
        if gpu_info.get('available'):
            print(f"   GPU: {gpu_info.get('device_name', 'N/A')}")
            print(f"   VRAM: {gpu_info.get('total_memory', 0) / 1024**3:.1f}GB")
        else:
            print("   GPU não disponível - usando CPU")
        
        print("\n4. Baixando arquivo de áudio...")
        start_time = time.time()
        
        # Usar DownloadService para baixar o arquivo
        from src.services.download_service import DownloadService
        download_service = DownloadService()
        
        audio_path = download_service.download_audio_file(
            audio_msg['conversation_id'],
            str(audio_msg['message_id']),
            audio_msg['file_url']
        )
        
        download_time = time.time() - start_time
        
        if audio_path:
            print(f"   Download concluído em {download_time:.2f}s")
            print(f"   Arquivo: {audio_path}")
            
            # Verificar tamanho do arquivo
            file_size = Path(audio_path).stat().st_size
            print(f"   Tamanho: {file_size / 1024:.1f} KB")
            
            print("\n5. Transcrevendo áudio...")
            transcription_start = time.time()
            
            result = audio_service.transcribe_file(audio_path)
            
            transcription_time = time.time() - transcription_start
            
            if result:
                print(f"   Transcrição concluída em {transcription_time:.2f}s")
                print(f"   Texto ({len(result['text'])} chars): {result['text'][:100]}...")
                print(f"   Confiança: {result['confidence']:.2f}")
                print(f"   Duração: {result['duration']:.1f}s")
                print(f"   Idioma: {result.get('language', 'N/A')}")
                
                print("\n6. Salvando transcrição no MongoDB...")
                success = db_service.update_audio_transcription(
                    audio_msg['conversation_id'],
                    audio_msg['contact_idx'],
                    audio_msg['message_idx'],
                    result['text'],
                    {
                        'confidence': result['confidence'],
                        'duration': result['duration'],
                        'language': result.get('language'),
                        'transcription_time': transcription_time,
                        'file_size': file_size
                    }
                )
                
                if success:
                    print("   Transcrição salva com sucesso!")
                else:
                    print("   Erro ao salvar transcrição")
                
                # Salvar também em arquivo local para verificação
                output_file = Path("output") / f"transcricao_{audio_msg['message_id']}.txt"
                output_file.parent.mkdir(exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"ID: {audio_msg['message_id']}\n")
                    f.write(f"URL: {audio_msg.get('file_url', 'N/A')}\n")
                    f.write(f"Confiança: {result['confidence']:.2f}\n")
                    f.write(f"Duração: {result['duration']:.1f}s\n")
                    f.write(f"Tempo transcrição: {transcription_time:.2f}s\n")
                    f.write(f"Tamanho arquivo: {file_size} bytes\n")
                    f.write("-" * 50 + "\n")
                    f.write(result['text'])
                
                print(f"   Backup salvo em: {output_file}")
                
            else:
                print("   Falha na transcrição")
        else:
            print("   Falha no download do áudio")
        
        # Limpeza
        audio_service.close()
        download_service.close()
        db_service.close()
        
        print("\nTeste de transcrição concluído!")
        
    except Exception as e:
        print(f"\nErro no teste: {e}")
        import traceback
        traceback.print_exc()
        print("Verifique se o sistema está configurado corretamente")

def main():
    """Função principal - executa teste real de transcrição"""
    print("Iniciando teste real de transcrição...")
    teste_real_transcricao()

if __name__ == "__main__":
    main()
