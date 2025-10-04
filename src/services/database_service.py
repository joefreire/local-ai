"""
Service para operações de banco de dados MongoDB
"""
import pymongo
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Optional, Any

from .base_service import BaseService
from ..config import Config

class DatabaseService(BaseService):
    """Service para operações MongoDB"""
    
    def _initialize(self):
        """Inicializar conexão MongoDB"""
        self.client = pymongo.MongoClient(Config.MONGODB_URI)
        self.db = self.client[Config.MONGODB_DATABASE]
        self._test_connection()
    
    def _test_connection(self):
        """Testar conexão com MongoDB"""
        try:
            self.client.admin.command('ping')
            self.logger.info(f"✅ Conectado ao MongoDB: {Config.MONGODB_DATABASE}")
        except Exception as e:
            self.logger.error(f"❌ Erro ao conectar MongoDB: {e}")
            raise
    
    def get_conversations_with_pending_audios(self, limit: int = 100) -> List[Dict]:
        """Buscar conversas com áudios pendentes"""
        self._ensure_initialized()
        self._log_operation("busca de conversas pendentes", {"limit": limit})
        
        query = {
            # Excluir conversas já processadas
            "audio_processing_status": {"$ne": "completed"},
            # Buscar conversas com áudios
            "$or": [
                {"audio_messages": {"$gt": 0}},
                {"media_messages": {"$gt": 0}},
                {"contacts.messages.type": "audio"},
                {"contacts.messages.media_type": "audio"}
            ]
        }
        
        try:
            cursor = self.db.diarios.find(query).limit(limit)
            conversations = []
            
            for conv in cursor:
                # Verificar se realmente tem áudios pendentes
                has_pending_audios = self._has_pending_audios(conv)
                if has_pending_audios:
                    conv["_id"] = str(conv["_id"])
                    conversations.append(conv)
            
            self._log_success("busca de conversas pendentes", {"encontradas": len(conversations)})
            return conversations
            
        except Exception as e:
            self._log_error("busca de conversas pendentes", e)
            raise

    def _has_pending_audios(self, conversation: Dict) -> bool:
        """Verificar se a conversa tem áudios pendentes de processamento"""
        try:
            for contact in conversation.get('contacts', []):
                for message in contact.get('messages', []):
                    if self._is_audio_message(message):
                        # Se não tem transcrição ou status não é completed
                        if (not message.get('audio_transcription') and 
                            message.get('transcription_status') != 'completed'):
                            return True
            return False
        except Exception:
            return False
    
    def get_pending_audios_for_conversation(self, conversation_id: str) -> List[Dict]:
        """Extrair áudios pendentes de uma conversa"""
        self._ensure_initialized()
        self._log_operation("extração de áudios pendentes", {"conversation_id": conversation_id})
        
        try:
            conversation = self.db.diarios.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return []
            
            pending_audios = []
            contacts = conversation.get('contacts', [])
            
            for contact_idx, contact in enumerate(contacts):
                messages = contact.get('messages', [])
                
                for msg_idx, message in enumerate(messages):
                    if self._is_audio_message(message) and not self._has_transcription(message):
                        audio_info = self._create_audio_info(
                            conversation_id, contact_idx, msg_idx, 
                            message, contact
                        )
                        pending_audios.append(audio_info)
            
            self._log_success("extração de áudios pendentes", {"encontrados": len(pending_audios)})
            return pending_audios
            
        except Exception as e:
            self._log_error("extração de áudios pendentes", e)
            return []
    
    def _is_audio_message(self, message: Dict) -> bool:
        """Verificar se mensagem é áudio"""
        return (
            message.get('media_type') == 'audio' or
            message.get('is_audio', False) or
            message.get('type') == 'audio' or
            str(message.get('media_url', '')).endswith(('.mp3', '.wav', '.ogg', '.m4a', '.oga')) or
            str(message.get('direct_media_url', '')).endswith(('.mp3', '.wav', '.ogg', '.m4a', '.oga'))
        )
    
    def _has_transcription(self, message: Dict) -> bool:
        """Verificar se mensagem já tem transcrição"""
        return bool(
            message.get('audio_transcription') or
            message.get('transcription') or 
            message.get('transcription_text')
        )
    
    def _create_audio_info(self, conversation_id: str, contact_idx: int, 
                          message_idx: int, message: Dict, contact: Dict) -> Dict:
        """Criar informações do áudio"""
        return {
            'conversation_id': conversation_id,
            'contact_idx': contact_idx,
            'message_idx': message_idx,
            'message_id': message.get('_id'),
            'contact_name': contact.get('contact_name', 'Desconhecido'),
            'file_url': self._get_audio_url(message),
            'created_at': message.get('created_at'),
            'body': message.get('body', 'Áudio')
        }
    
    def _get_audio_url(self, message: Dict) -> Optional[str]:
        """Obter URL do áudio priorizando diferentes campos"""
        return (
            message.get('direct_media_url') or 
            message.get('download_url') or 
            message.get('media_url') or
            message.get('file_url') or
            message.get('file_path')
        )
    
    def update_audio_transcription(self, conversation_id: str, contact_idx: int, 
                                 message_idx: int, transcription: Dict) -> bool:
        """Atualizar transcrição de áudio"""
        self._log_operation("atualização de transcrição", {
            "conversation_id": conversation_id,
            "contact_idx": contact_idx,
            "message_idx": message_idx
        })
        
        try:
            result = self.db.diarios.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        f"contacts.{contact_idx}.messages.{message_idx}.audio_transcription": transcription["text"],
                        f"contacts.{contact_idx}.messages.{message_idx}.transcription_data": transcription,
                        f"contacts.{contact_idx}.messages.{message_idx}.transcription_status": "completed",
                        f"contacts.{contact_idx}.messages.{message_idx}.transcribed_at": datetime.now(),
                        "updated_at": datetime.now()
                    }
                }
            )
            
            success = result.modified_count > 0
            
            # Verificar se todos os áudios da conversa foram processados
            if success:
                self._check_and_update_conversation_status(conversation_id)
            
            self._log_success("atualização de transcrição", {"modified": result.modified_count})
            return success
            
        except Exception as e:
            self._log_error("atualização de transcrição", e)
            return False

    def _check_and_update_conversation_status(self, conversation_id: str):
        """Verificar se todos os áudios da conversa foram processados e atualizar status"""
        try:
            # Buscar a conversa
            conversation = self.db.diarios.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return
            
            # Contar áudios pendentes
            total_audios = 0
            processed_audios = 0
            
            for contact in conversation.get('contacts', []):
                for message in contact.get('messages', []):
                    if self._is_audio_message(message):
                        total_audios += 1
                        if message.get('transcription_status') == 'completed':
                            processed_audios += 1
            
            # Se todos os áudios foram processados, marcar conversa como completa
            if total_audios > 0 and processed_audios == total_audios:
                self.db.diarios.update_one(
                    {"_id": ObjectId(conversation_id)},
                    {
                        "$set": {
                            "audio_processing_status": "completed",
                            "audio_processing_completed_at": datetime.now(),
                            "audio_processing_stats": {
                                "total_audios": total_audios,
                                "processed_audios": processed_audios,
                                "completion_date": datetime.now()
                            }
                        }
                    }
                )
                self.logger.info(f"✅ Conversa {conversation_id} marcada como processada: {processed_audios}/{total_audios} áudios")
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status da conversa: {e}")
    
    def update_conversation_status(self, conversation_id: str, status: str) -> bool:
        """Atualizar status de processamento da conversa"""
        self._log_operation("atualização de status", {
            "conversation_id": conversation_id,
            "status": status
        })
        
        try:
            result = self.db.diarios.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        "status_audios": status,
                        "updated_at": datetime.now()
                    }
                }
            )
            
            success = result.modified_count > 0
            self._log_success("atualização de status", {"modified": result.modified_count})
            return success
            
        except Exception as e:
            self._log_error("atualização de status", e)
            return False
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Obter estatísticas das conversas"""
        self._ensure_initialized()
        self._log_operation("obtenção de estatísticas")
        
        try:
            total_conversations = self.db.diarios.count_documents({})
            
            audio_conversations = self.db.diarios.count_documents({
                "$or": [
                    {"audio_messages": {"$gt": 0}},
                    {"media_messages": {"$gt": 0}}
                ]
            })
            
            # Conversas com áudios pendentes (não processadas)
            pending_conversations = self.db.diarios.count_documents({
                "audio_processing_status": {"$ne": "completed"},
                "$or": [
                    {"audio_messages": {"$gt": 0}},
                    {"media_messages": {"$gt": 0}}
                ]
            })
            
            # Conversas completamente processadas
            completed_conversations = self.db.diarios.count_documents({
                "audio_processing_status": "completed"
            })
            
            stats = {
                "total_conversations": total_conversations,
                "audio_conversations": audio_conversations,
                "pending_conversations": pending_conversations,
                "completed_conversations": completed_conversations
            }
            
            self._log_success("obtenção de estatísticas", stats)
            return stats
            
        except Exception as e:
            self._log_error("obtenção de estatísticas", e)
            return {}

    def get_processing_status(self, conversation_id: str) -> Dict:
        """Obter status de processamento de uma conversa específica"""
        self._ensure_initialized()
        
        try:
            conversation = self.db.diarios.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return {"error": "Conversa não encontrada"}
            
            # Contar áudios
            total_audios = 0
            processed_audios = 0
            
            for contact in conversation.get('contacts', []):
                for message in contact.get('messages', []):
                    if self._is_audio_message(message):
                        total_audios += 1
                        if message.get('transcription_status') == 'completed':
                            processed_audios += 1
            
            status = {
                "conversation_id": conversation_id,
                "audio_processing_status": conversation.get('audio_processing_status', 'pending'),
                "total_audios": total_audios,
                "processed_audios": processed_audios,
                "completion_percentage": (processed_audios / total_audios * 100) if total_audios > 0 else 0,
                "completed_at": conversation.get('audio_processing_completed_at'),
                "stats": conversation.get('audio_processing_stats', {})
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Erro ao obter status de processamento: {e}")
            return {"error": str(e)}
    
    def get_conversation_text_for_analysis(self, conversation_id: str) -> Dict:
        """Obter texto de conversa para análise"""
        self._ensure_initialized()
        try:
            conversation = self.db.diarios.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return {}
            
            conversation_text = {
                'conversation_id': conversation_id,
                'user_name': conversation.get('user_name'),
                'date': conversation.get('date_formatted'),
                'contacts': []
            }
            
            for contact in conversation.get('contacts', []):
                contact_data = {
                    'contact_name': contact.get('contact_name'),
                    'messages': []
                }
                
                for message in contact.get('messages', []):
                    # Incluir texto da mensagem ou transcrição
                    message_text = (
                        message.get('audio_transcription') or 
                        message.get('body', '') or 
                        message.get('text', '')
                    )
                    
                    if message_text:
                        contact_data['messages'].append({
                            'timestamp': message.get('created_at'),
                            'text': message_text,
                            'message_type': 'audio' if self._is_audio_message(message) else 'text'
                        })
                
                conversation_text['contacts'].append(contact_data)
            
            return conversation_text
            
        except Exception as e:
            self.logger.error(f"Erro ao obter texto da conversa: {e}")
            return {}
    
    def save_conversation_analysis(self, conversation_id: str, analysis: Dict):
        """Salvar análise da conversa no MongoDB"""
        try:
            analysis_data = {
                'conversation_analysis': analysis,
                'analyzed_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            result = self.db.diarios.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": analysis_data}
            )
            
            success = result.modified_count > 0
            self.logger.info(f"Análise salva para conversa {conversation_id}: {success}")
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar análise: {e}")
            return False
    
    def _cleanup(self):
        """Fechar conexão MongoDB"""
        if hasattr(self, 'client'):
            self.client.close()
