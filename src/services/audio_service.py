"""
Service para processamento de áudio com Whisper
"""
import torch
import whisper
import tempfile
import shutil
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import time
from datetime import datetime

from .base_service import BaseService
from ..config import Config

class AudioService(BaseService):
    """Service para processamento de áudio"""
    
    def _initialize(self):
        """Inicializar modelo Whisper"""
        self.device = self._setup_gpu()
        self.model = None
        self._load_whisper_model()
    
    def _setup_gpu(self) -> str:
        """Configurar GPU para processamento com fallback automático"""
        try:
            if torch.cuda.is_available():
                device = f"cuda:{torch.cuda.current_device()}"
                
                # Configurar memória apenas se disponível
                try:
                    torch.cuda.set_per_process_memory_fraction(Config.GPU_MEMORY_FRACTION)
                except Exception as e:
                    self.logger.warning(f"⚠️ Não foi possível configurar memória GPU: {e}")
                
                gpu_name = torch.cuda.get_device_name()
                total_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                
                self.logger.info(f"🚀 GPU detectada: {gpu_name} ({total_memory:.1f}GB)")
                self.logger.info(f"🔧 Memória configurada: {Config.GPU_MEMORY_FRACTION*100}%")
                
                return device
            else:
                self.logger.info("💻 GPU não disponível - usando CPU (compatível com todos os sistemas)")
                return "cpu"
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao detectar GPU: {e} - usando CPU")
            return "cpu"
    
    def _load_whisper_model(self):
        """Carregar modelo Whisper"""
        try:
            self.logger.info(f"📥 Carregando modelo Whisper: {Config.WHISPER_MODEL}")
            self.model = whisper.load_model(
                Config.WHISPER_MODEL,
                device=self.device,
                download_root=str(Config.MODELS_DIR)
            )
            self.logger.info("✅ Modelo Whisper carregado")
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar modelo: {e}")
            raise
    
    def transcribe_file(self, file_path: str) -> Optional[Dict]:
        """Transcrever arquivo individual"""
        self._ensure_initialized()
        self._log_operation("transcrição de arquivo", {"file_path": file_path})
        
        try:
            if not Path(file_path).exists():
                self.logger.error(f"Arquivo não encontrado: {file_path}")
                return None
            
            # Carregar áudio
            audio = whisper.load_audio(file_path)
            audio = whisper.pad_or_trim(audio)
            
            # Transcrever
            result = self.model.transcribe(
                audio,
                language=Config.WHISPER_LANGUAGE,
                word_timestamps=True,
                fp16=torch.cuda.is_available()
            )
            
            transcription = {
                'text': result['text'].strip(),
                'segments': result.get('segments', []),
                'language': result.get('language', Config.WHISPER_LANGUAGE),
                'file_path': file_path,
                'duration': len(audio) / 16000,
                'confidence': self._calculate_confidence(result.get('segments', [])),
                'transcribed_at': datetime.now().isoformat()
            }
            
            self._log_success("transcrição de arquivo", {
                "text_length": len(transcription['text']),
                "confidence": transcription['confidence']
            })
            
            return transcription
            
        except Exception as e:
            self._log_error("transcrição de arquivo", e)
            return None
    
    def transcribe_batch(self, audio_files: List[str]) -> List[Optional[Dict]]:
        """Transcrever múltiplos arquivos em batch"""
        self._log_operation("transcrição em batch", {"file_count": len(audio_files)})
        
        results = []
        batch_size = Config.GPU_BATCH_SIZE
        
        for i in range(0, len(audio_files), batch_size):
            batch = audio_files[i:i + batch_size]
            batch_results = self._transcribe_batch_gpu(batch)
            results.extend(batch_results)
        
        successful = len([r for r in results if r is not None])
        self._log_success("transcrição em batch", {
            "total": len(audio_files),
            "successful": successful,
            "failed": len(audio_files) - successful
        })
        
        return results
    
    def _transcribe_batch_gpu(self, audio_files: List[str]) -> List[Optional[Dict]]:
        """Transcrever batch na GPU"""
        results = []
        
        for file_path in audio_files:
            try:
                result = self.transcribe_file(file_path)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Erro na transcrição de {file_path}: {e}")
                results.append(None)
        
        return results
    
    def _calculate_confidence(self, segments: List[Dict]) -> float:
        """Calcular confiança média da transcrição"""
        if not segments:
            return 0.0
        
        confidences = []
        for segment in segments:
            if 'avg_logprob' in segment:
                # Converter log probability para confiança (0-1)
                confidence = min(1.0, max(0.0, (segment['avg_logprob'] + 1.0)))
                confidences.append(confidence)
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """Obter informações da GPU com fallback para CPU"""
        self._ensure_initialized()
        
        try:
            if torch.cuda.is_available():
                return {
                    'available': True,
                    'device_name': torch.cuda.get_device_name(),
                    'total_memory': torch.cuda.get_device_properties(0).total_memory,
                    'allocated_memory': torch.cuda.memory_allocated(),
                    'cached_memory': torch.cuda.memory_reserved(),
                    'memory_fraction': Config.GPU_MEMORY_FRACTION,
                    'device_type': 'GPU'
                }
            else:
                return {
                    'available': False,
                    'device_name': 'CPU',
                    'device_type': 'CPU',
                    'message': 'GPU não disponível - usando CPU (compatível com todos os sistemas)'
                }
        except Exception as e:
            return {
                'available': False,
                'device_name': 'CPU',
                'device_type': 'CPU',
                'error': str(e),
                'message': 'Erro ao detectar GPU - usando CPU'
            }
    
    def test_transcription(self, file_path: str) -> bool:
        """Testar transcrição com arquivo"""
        self.logger.info(f"🧪 Testando transcrição: {file_path}")
        
        try:
            result = self.transcribe_file(file_path)
            if result:
                self.logger.info(f"✅ Teste OK - Texto: {result['text'][:100]}...")
                return True
            else:
                self.logger.error("❌ Teste falhou")
                return False
        except Exception as e:
            self.logger.error(f"❌ Erro no teste: {e}")
            return False

    def save_transcription_to_json(self, conversation_id: str, message_id: str, 
                                 transcription_data: Dict) -> Optional[str]:
        """Salvar transcrição em arquivo JSON no mesmo padrão dos downloads"""
        self._ensure_initialized()
        
        try:
            # Criar diretório da conversa
            conv_dir = Config.TRANSCRIPTIONS_DIR / conversation_id
            conv_dir.mkdir(exist_ok=True)
            
            # Caminho do arquivo JSON
            json_path = conv_dir / f"{message_id}.json"
            
            # Se já existe, retornar
            if json_path.exists():
                self.logger.info(f"Transcrição já existe: {json_path.name}")
                return str(json_path)
            
            # Preparar dados para salvar
            save_data = {
                "conversation_id": conversation_id,
                "message_id": message_id,
                "transcription": transcription_data,
                "created_at": datetime.now().isoformat(),
                "whisper_model": Config.WHISPER_MODEL,
                "device": self.device
            }
            
            # Salvar JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ Transcrição salva: {json_path.name}")
            return str(json_path)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar transcrição: {e}")
            return None

    def load_transcription_from_json(self, conversation_id: str, message_id: str) -> Optional[Dict]:
        """Carregar transcrição de arquivo JSON"""
        self._ensure_initialized()
        
        try:
            json_path = Config.TRANSCRIPTIONS_DIR / conversation_id / f"{message_id}.json"
            
            if not json_path.exists():
                return None
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('transcription')
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar transcrição: {e}")
            return None
