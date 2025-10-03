"""
Gerenciador de filas simples usando apenas MongoDB
"""
import logging
import threading
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from .database import DatabaseManager
from .audio_processor import GPUAudioProcessor
from .conversation_analyzer import ConversationAnalyzer
from .config import Config

logger = logging.getLogger(__name__)

class SimpleQueueManager:
    """Gerenciador de filas simples usando MongoDB"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.audio_processor = GPUAudioProcessor()
        self.analyzer = ConversationAnalyzer()
        self.processing_active = False
        self.processing_thread = None
        self.max_workers = Config.MAX_CONCURRENT_JOBS
    
    def start_processing(self, interval: int = 30):
        """Iniciar processamento automático"""
        if self.processing_active:
            logger.warning("⚠️ Processamento já está ativo")
            return
        
        self.processing_active = True
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            args=(interval,),
            daemon=True
        )
        self.processing_thread.start()
        
        logger.info(f"🚀 Processamento automático iniciado (intervalo: {interval}s)")
    
    def stop_processing(self):
        """Parar processamento automático"""
        self.processing_active = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        logger.info("🛑 Processamento automático parado")
    
    def _processing_loop(self, interval: int):
        """Loop de processamento automático"""
        while self.processing_active:
            try:
                # Buscar conversas pendentes
                pending_conversations = self.discover_pending_conversations(limit=10)
                
                if pending_conversations:
                    logger.info(f"📋 Encontradas {len(pending_conversations)} conversas pendentes")
                    
                    # Processar em paralelo
                    self._process_conversations_parallel(pending_conversations)
                else:
                    logger.debug("📭 Nenhuma conversa pendente encontrada")
                
            except Exception as e:
                logger.error(f"❌ Erro no loop de processamento: {e}")
            
            time.sleep(interval)
    
    def discover_pending_conversations(self, limit: int = 50) -> List[Dict]:
        """Descobrir conversas com áudios pendentes"""
        conversations = self.db.get_conversations_with_pending_audios(limit)
        
        logger.info(f"🔍 Descobertas {len(conversations)} conversas pendentes")
        return conversations
    
    def _process_conversations_parallel(self, conversations: List[Dict]):
        """Processar múltiplas conversas em paralelo"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter todas as conversas para processamento
            future_to_conv = {
                executor.submit(self.process_conversation_complete, conv['_id']): conv
                for conv in conversations
            }
            
            # Processar resultados conforme completam
            for future in as_completed(future_to_conv):
                conv = future_to_conv[future]
                try:
                    result = future.result()
                    logger.info(f"✅ Conversa {conv['_id'][:8]} processada: {result.get('status', 'unknown')}")
                except Exception as e:
                    logger.error(f"❌ Erro ao processar conversa {conv['_id'][:8]}: {e}")
    
    def process_conversation_complete(self, conversation_id: str) -> Dict[str, Any]:
        """Processar conversa completa: download + transcrição + análise"""
        logger.info(f"🚀 Processando conversa {conversation_id[:8]}")
        
        try:
            # Atualizar status para processando
            self.db.update_conversation_audio_status(conversation_id, "processing")
            
            # 1. Obter áudios pendentes
            audio_urls = self.db.get_pending_audios_for_conversation(conversation_id)
            
            if not audio_urls:
                self.db.update_conversation_audio_status(conversation_id, "completed")
                return {
                    'conversation_id': conversation_id,
                    'status': 'no_audios',
                    'message': 'Nenhum áudio pendente encontrado'
                }
            
            logger.info(f"🎵 Encontrados {len(audio_urls)} áudios para processar")
            
            # 2. Processar áudios (download + transcrição)
            transcription_results = self.audio_processor.process_audio_batch(audio_urls)
            
            # 3. Salvar transcrições no MongoDB
            successful_transcriptions = 0
            failed_transcriptions = 0
            
            for audio_info, transcription in transcription_results:
                if transcription:
                    success = self.db.update_audio_transcription(
                        conversation_id,
                        audio_info['contact_idx'],
                        audio_info['message_idx'],
                        transcription
                    )
                    
                    if success:
                        successful_transcriptions += 1
                    else:
                        failed_transcriptions += 1
                else:
                    failed_transcriptions += 1
            
            # 4. Atualizar resumo de transcrições
            self.db.update_audio_transcriptions_summary(conversation_id)
            
            # 5. Analisar conversa (se houver transcrições)
            analysis_result = None
            if successful_transcriptions > 0:
                try:
                    conversation_data = self.db.get_conversation_text_for_analysis(conversation_id)
                    if conversation_data:
                        analysis = self.analyzer.analyze_conversation(conversation_data)
                        if 'error' not in analysis:
                            self.db.save_conversation_analysis(conversation_id, analysis)
                            analysis_result = analysis
                except Exception as e:
                    logger.error(f"❌ Erro na análise da conversa: {e}")
            
            # 6. Determinar status final
            if failed_transcriptions == 0:
                final_status = "completed"
            elif successful_transcriptions > 0:
                final_status = "partial"
            else:
                final_status = "error"
            
            self.db.update_conversation_audio_status(conversation_id, final_status)
            
            result = {
                'conversation_id': conversation_id,
                'status': final_status,
                'total_audios': len(audio_urls),
                'successful_transcriptions': successful_transcriptions,
                'failed_transcriptions': failed_transcriptions,
                'analysis_completed': analysis_result is not None,
                'processed_at': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Conversa {conversation_id[:8]} processada: {successful_transcriptions}/{len(audio_urls)} transcrições")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento da conversa {conversation_id}: {e}")
            
            # Marcar como erro
            try:
                self.db.update_conversation_audio_status(conversation_id, "error")
            except:
                pass
            
            return {
                'conversation_id': conversation_id,
                'status': 'error',
                'error': str(e)
            }
    
    def process_single_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Processar uma única conversa"""
        return self.process_conversation_complete(conversation_id)
    
    def process_multiple_conversations(self, conversation_ids: List[str]) -> List[Dict[str, Any]]:
        """Processar múltiplas conversas"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {
                executor.submit(self.process_conversation_complete, conv_id): conv_id
                for conv_id in conversation_ids
            }
            
            for future in as_completed(future_to_id):
                conv_id = future_to_id[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Erro ao processar conversa {conv_id}: {e}")
                    results.append({
                        'conversation_id': conv_id,
                        'status': 'error',
                        'error': str(e)
                    })
        
        return results
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Obter status do processamento"""
        try:
            # Contar conversas por status
            conversations = self.db.get_conversations_with_pending_audios(10000)
            
            status_counts = {}
            total_audios = 0
            total_transcribed = 0
            
            for conv in conversations:
                status = conv.get('status_audios', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Contar áudios
                audio_urls = self.db.get_pending_audios_for_conversation(conv['_id'])
                total_audios += len(audio_urls)
                
                # Contar transcrições
                transcription_summary = conv.get('audio_transcriptions', {})
                if transcription_summary:
                    total_transcribed += transcription_summary.get('transcribed_audios', 0)
            
            return {
                'processing_active': self.processing_active,
                'max_workers': self.max_workers,
                'conversations_by_status': status_counts,
                'total_conversations': len(conversations),
                'total_audios_pending': total_audios,
                'total_audios_transcribed': total_transcribed,
                'transcription_progress': (total_transcribed / (total_audios + total_transcribed) * 100) if (total_audios + total_transcribed) > 0 else 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter status: {e}")
            return {'error': str(e)}
    
    def get_gpu_status(self) -> Dict[str, Any]:
        """Obter status da GPU"""
        try:
            return self.audio_processor.get_gpu_memory_info()
        except Exception as e:
            logger.error(f"❌ Erro ao obter status GPU: {e}")
            return {'error': str(e)}
    
    def cleanup_failed_conversations(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Limpar conversas com erro antigas"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            # Buscar conversas com erro antigas
            conversations = self.db.get_conversations_with_pending_audios(10000)
            failed_conversations = [
                conv for conv in conversations
                if conv.get('status_audios') == 'error' and 
                conv.get('updated_at', datetime.min) < cutoff_time
            ]
            
            # Resetar status para pending
            reset_count = 0
            for conv in failed_conversations:
                try:
                    self.db.update_conversation_audio_status(conv['_id'], "pending")
                    reset_count += 1
                except Exception as e:
                    logger.error(f"❌ Erro ao resetar conversa {conv['_id']}: {e}")
            
            return {
                'found_failed': len(failed_conversations),
                'reset_to_pending': reset_count,
                'max_age_hours': max_age_hours,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na limpeza: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Fechar gerenciador"""
        self.stop_processing()
        self.db.close()
