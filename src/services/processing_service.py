"""
Service principal para processamento de conversas
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
import time

from .base_service import BaseService
from .database_service import DatabaseService
from .audio_service import AudioService
from .download_service import DownloadService
from .analysis_service import LlamaService
from ..config import Config

class ProcessingService(BaseService):
    """Service principal para processamento"""
    
    def _initialize(self):
        """Inicializar services"""
        self.db_service = DatabaseService()
        self.audio_service = AudioService()
        self.download_service = DownloadService()
        self.analysis_service = LlamaService()
        
        self.processing_active = False
        self.processing_thread = None
    
    def process_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Processar uma conversa completa"""
        self._log_operation("processamento de conversa", {"conversation_id": conversation_id})
        
        try:
            # Atualizar status
            self.db_service.update_conversation_status(conversation_id, "processing")
            
            # 1. Obter áudios pendentes
            audio_urls = self.db_service.get_pending_audios_for_conversation(conversation_id)
            
            if not audio_urls:
                self.db_service.update_conversation_status(conversation_id, "completed")
                return {
                    'conversation_id': conversation_id,
                    'status': 'no_audios',
                    'message': 'Nenhum áudio pendente'
                }
            
            # 2. Download dos áudios
            download_results = self.download_service.download_audio_batch(audio_urls)
            successful_downloads = [(info, path) for info, path in download_results if path is not None]
            
            if not successful_downloads:
                self.db_service.update_conversation_status(conversation_id, "error")
                return {
                    'conversation_id': conversation_id,
                    'status': 'download_failed',
                    'message': 'Falha no download dos áudios'
                }
            
            # 3. Transcrição
            transcription_results = self._process_transcriptions(successful_downloads)
            
            # 4. Análise da conversa
            analysis_result = None
            if transcription_results['successful'] > 0:
                analysis_result = self._analyze_conversation(conversation_id)
            
            # 5. Status final
            final_status = self._determine_final_status(transcription_results)
            self.db_service.update_conversation_status(conversation_id, final_status)
            
            result = {
                'conversation_id': conversation_id,
                'status': final_status,
                'total_audios': len(audio_urls),
                'downloaded': len(successful_downloads),
                'transcribed': transcription_results['successful'],
                'failed': transcription_results['failed'],
                'analysis_completed': analysis_result is not None,
                'processed_at': datetime.now().isoformat()
            }
            
            self._log_success("processamento de conversa", result)
            return result
            
        except Exception as e:
            self._log_error("processamento de conversa", e)
            self.db_service.update_conversation_status(conversation_id, "error")
            return {
                'conversation_id': conversation_id,
                'status': 'error',
                'error': str(e)
            }
    
    def _process_transcriptions(self, download_results: List) -> Dict[str, int]:
        """Processar transcrições"""
        successful = 0
        failed = 0
        
        for audio_info, file_path in download_results:
            try:
                # Transcrever
                transcription = self.audio_service.transcribe_file(file_path)
                
                if transcription:
                    # Adicionar metadados
                    transcription.update({
                        'conversation_id': audio_info['conversation_id'],
                        'message_id': audio_info['message_id'],
                        'contact_name': audio_info['contact_name'],
                        'transcribed_at': datetime.now().isoformat()
                    })
                    
                    # Salvar no banco
                    success = self.db_service.update_audio_transcription(
                        audio_info['conversation_id'],
                        audio_info['contact_idx'],
                        audio_info['message_idx'],
                        transcription
                    )
                    
                    if success:
                        successful += 1
                    else:
                        failed += 1
                else:
                    failed += 1
                    
            except Exception as e:
                self.logger.error(f"Erro na transcrição de {audio_info['message_id']}: {e}")
                failed += 1
        
        return {'successful': successful, 'failed': failed}
    
    def _analyze_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Analisar conversa"""
        try:
            # Obter dados da conversa
            conversation_data = self.db_service.get_conversation_text_for_analysis(conversation_id)
            
            if not conversation_data:
                return None
            
            # Analisar
            analysis = self.analysis_service.analyze_conversation(conversation_data)
            
            if 'error' not in analysis:
                # Salvar análise no banco
                self.db_service.save_conversation_analysis(conversation_id, analysis)
                return analysis
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro na análise da conversa {conversation_id}: {e}")
            return None
    
    def _determine_final_status(self, transcription_results: Dict[str, int]) -> str:
        """Determinar status final"""
        successful = transcription_results['successful']
        failed = transcription_results['failed']
        
        if failed == 0:
            return "completed"
        elif successful > 0:
            return "partial"
        else:
            return "error"
    
    def start_auto_processing(self, interval: int = 30):
        """Iniciar processamento automático"""
        if self.processing_active:
            self.logger.warning("Processamento já está ativo")
            return
        
        self.processing_active = True
        self.processing_thread = threading.Thread(
            target=self._auto_processing_loop,
            args=(interval,),
            daemon=True
        )
        self.processing_thread.start()
        
        self.logger.info(f"🚀 Processamento automático iniciado (intervalo: {interval}s)")
    
    def stop_auto_processing(self):
        """Parar processamento automático"""
        self.processing_active = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        self.logger.info("🛑 Processamento automático parado")
    
    def _auto_processing_loop(self, interval: int):
        """Loop de processamento automático"""
        while self.processing_active:
            try:
                # Buscar conversas pendentes
                pending_conversations = self.db_service.get_conversations_with_pending_audios(limit=5)
                
                if pending_conversations:
                    self.logger.info(f"Processando {len(pending_conversations)} conversas pendentes")
                    
                    # Processar cada conversa
                    for conv in pending_conversations:
                        if not self.processing_active:
                            break
                        
                        self.process_conversation(conv['_id'])
                else:
                    self.logger.debug("Nenhuma conversa pendente encontrada")
                
            except Exception as e:
                self.logger.error(f"Erro no loop de processamento: {e}")
            
            time.sleep(interval)
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Obter status do processamento"""
        try:
            stats = self.db_service.get_conversation_stats()
            
            return {
                'processing_active': self.processing_active,
                'max_workers': Config.MAX_CONCURRENT_JOBS,
                'conversation_stats': stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self._log_error("obtenção de status", e)
            return {'error': str(e)}
    
    def _cleanup(self):
        """Limpar recursos"""
        self.stop_auto_processing()
        
        if hasattr(self, 'db_service'):
            self.db_service.close()
        if hasattr(self, 'audio_service'):
            self.audio_service.close()
        if hasattr(self, 'download_service'):
            self.download_service.close()
        if hasattr(self, 'analysis_service'):
            self.analysis_service.close()
