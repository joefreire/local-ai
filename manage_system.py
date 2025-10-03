#!/usr/bin/env python3
"""
Script de gerenciamento do sistema simplificado
"""
import sys
import os
import argparse
import logging
from pathlib import Path

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

from src.queue_manager_simple import SimpleQueueManager
from src.database import DatabaseManager
from src.audio_processor import GPUAudioProcessor
from src.config import Config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_system():
    """Verificar sistema"""
    print("🔍 Verificando sistema...")
    
    # Verificar GPU
    try:
        processor = GPUAudioProcessor()
        gpu_info = processor.get_gpu_memory_info()
        if gpu_info.get('available'):
            print(f"✅ GPU: {gpu_info.get('device_name', 'N/A')}")
            print(f"   💾 VRAM: {gpu_info.get('total_memory', 0) / 1024**3:.1f}GB")
        else:
            print("⚠️ GPU não disponível - usando CPU")
    except Exception as e:
        print(f"❌ Erro ao verificar GPU: {e}")
    
    # Verificar MongoDB
    try:
        db = DatabaseManager()
        conversations = db.get_conversations_with_pending_audios(1)
        print(f"✅ MongoDB: {Config.MONGODB_DATABASE}")
        print(f"   📊 Conversas pendentes: {len(conversations)}")
    except Exception as e:
        print(f"❌ Erro ao conectar MongoDB: {e}")
    
    # Verificar Ollama
    try:
        from src.conversation_analyzer import ConversationAnalyzer
        analyzer = ConversationAnalyzer()
        if analyzer.test_model_availability():
            print(f"✅ Ollama: {Config.OLLAMA_MODEL}")
        else:
            print("⚠️ Ollama não disponível")
    except Exception as e:
        print(f"⚠️ Ollama: {e}")

def start_processing():
    """Iniciar processamento automático"""
    print("🚀 Iniciando processamento automático...")
    
    try:
        queue_manager = SimpleQueueManager()
        queue_manager.start_processing(interval=30)
        
        print("✅ Processamento iniciado")
        print("💡 Use Ctrl+C para parar")
        
        # Manter rodando
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Parando processamento...")
            queue_manager.stop_processing()
            queue_manager.close()
            print("✅ Processamento parado")
            
    except Exception as e:
        print(f"❌ Erro ao iniciar processamento: {e}")

def process_conversations(conversation_ids):
    """Processar conversas específicas"""
    print(f"📋 Processando {len(conversation_ids)} conversas...")
    
    try:
        queue_manager = SimpleQueueManager()
        
        if len(conversation_ids) == 1:
            result = queue_manager.process_single_conversation(conversation_ids[0])
        else:
            results = queue_manager.process_multiple_conversations(conversation_ids)
            successful = len([r for r in results if r.get('status') not in ['error']])
            result = {
                'total': len(conversation_ids),
                'successful': successful,
                'failed': len(conversation_ids) - successful,
                'results': results
            }
        
        print("✅ Processamento concluído:")
        if isinstance(result, dict) and 'results' in result:
            print(f"   📊 Total: {result['total']}")
            print(f"   ✅ Sucessos: {result['successful']}")
            print(f"   ❌ Falhas: {result['failed']}")
        else:
            print(f"   📊 Status: {result.get('status', 'unknown')}")
        
        queue_manager.close()
        
    except Exception as e:
        print(f"❌ Erro ao processar conversas: {e}")

def show_status():
    """Mostrar status do sistema"""
    print("📊 Status do sistema:")
    
    try:
        queue_manager = SimpleQueueManager()
        status = queue_manager.get_processing_status()
        
        print(f"🔄 Processamento ativo: {'Sim' if status.get('processing_active') else 'Não'}")
        print(f"👥 Workers máximos: {status.get('max_workers', 0)}")
        print(f"📋 Conversas pendentes: {status.get('total_conversations', 0)}")
        print(f"🎵 Áudios pendentes: {status.get('total_audios_pending', 0)}")
        print(f"✅ Áudios transcritos: {status.get('total_audios_transcribed', 0)}")
        print(f"📈 Progresso: {status.get('transcription_progress', 0):.1f}%")
        
        # Status por conversa
        conversations_by_status = status.get('conversations_by_status', {})
        if conversations_by_status:
            print("\n📊 Conversas por status:")
            for status_name, count in conversations_by_status.items():
                print(f"   {status_name}: {count}")
        
        queue_manager.close()
        
    except Exception as e:
        print(f"❌ Erro ao obter status: {e}")

def discover_pending():
    """Descobrir conversas pendentes"""
    print("🔍 Descobrindo conversas pendentes...")
    
    try:
        queue_manager = SimpleQueueManager()
        conversations = queue_manager.discover_pending_conversations(limit=20)
        
        if conversations:
            print(f"📋 Encontradas {len(conversations)} conversas pendentes:")
            for conv in conversations[:10]:  # Mostrar apenas as primeiras 10
                conv_id = conv['_id'][:8]
                user_name = conv.get('user_name', 'Desconhecido')
                status = conv.get('status_audios', 'unknown')
                print(f"   📁 {conv_id} - {user_name} ({status})")
            
            if len(conversations) > 10:
                print(f"   ... e mais {len(conversations) - 10} conversas")
        else:
            print("📭 Nenhuma conversa pendente encontrada")
        
        queue_manager.close()
        
    except Exception as e:
        print(f"❌ Erro ao descobrir conversas: {e}")

def cleanup_failed():
    """Limpar conversas com erro"""
    print("🧹 Limpando conversas com erro...")
    
    try:
        queue_manager = SimpleQueueManager()
        result = queue_manager.cleanup_failed_conversations(max_age_hours=24)
        
        print(f"✅ Limpeza concluída:")
        print(f"   🔍 Conversas com erro encontradas: {result.get('found_failed', 0)}")
        print(f"   🔄 Resetadas para pending: {result.get('reset_to_pending', 0)}")
        
        queue_manager.close()
        
    except Exception as e:
        print(f"❌ Erro na limpeza: {e}")

def start_api():
    """Iniciar API"""
    print("🌐 Iniciando API...")
    
    try:
        import uvicorn
        from src.api_simple import app
        
        print("✅ API iniciada em http://localhost:8000")
        print("📚 Documentação: http://localhost:8000/docs")
        print("💡 Use Ctrl+C para parar")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Erro ao iniciar API: {e}")

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Gerenciador do Sistema de Transcrição")
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')
    
    # Comando check
    subparsers.add_parser('check', help='Verificar sistema')
    
    # Comando start
    subparsers.add_parser('start', help='Iniciar processamento automático')
    
    # Comando process
    process_parser = subparsers.add_parser('process', help='Processar conversas específicas')
    process_parser.add_argument('conversation_ids', nargs='+', help='IDs das conversas')
    
    # Comando status
    subparsers.add_parser('status', help='Mostrar status do sistema')
    
    # Comando discover
    subparsers.add_parser('discover', help='Descobrir conversas pendentes')
    
    # Comando cleanup
    subparsers.add_parser('cleanup', help='Limpar conversas com erro')
    
    # Comando api
    subparsers.add_parser('api', help='Iniciar API')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🎙️ Sistema de Transcrição WhatsApp - Simplificado")
    print("=" * 50)
    
    if args.command == 'check':
        check_system()
    elif args.command == 'start':
        start_processing()
    elif args.command == 'process':
        process_conversations(args.conversation_ids)
    elif args.command == 'status':
        show_status()
    elif args.command == 'discover':
        discover_pending()
    elif args.command == 'cleanup':
        cleanup_failed()
    elif args.command == 'api':
        start_api()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
