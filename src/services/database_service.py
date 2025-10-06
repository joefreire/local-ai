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
        self._create_indexes()
    
    def _test_connection(self):
        """Testar conexão com MongoDB"""
        try:
            self.client.admin.command('ping')
            self.logger.info(f"✅ Conectado ao MongoDB: {Config.MONGODB_DATABASE}")
        except Exception as e:
            self.logger.error(f"❌ Erro ao conectar MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Criar índices para otimizar consultas"""
        try:
            # Índices para collection de transcrições
            self.db.transcriptions.create_index("mensagem_id", unique=True)
            self.db.transcriptions.create_index("user_id")
            self.db.transcriptions.create_index("company_id")
            self.db.transcriptions.create_index("server_name")
            self.db.transcriptions.create_index("created_at")
            self.db.transcriptions.create_index([("user_id", 1), ("created_at", -1)])
            
            # Índices para collection de análises de imagem
            self.db.image_analyses.create_index("mensagem_id", unique=True)
            self.db.image_analyses.create_index("user_id")
            self.db.image_analyses.create_index("company_id")
            self.db.image_analyses.create_index("server_name")
            self.db.image_analyses.create_index("created_at")
            self.db.image_analyses.create_index([("user_id", 1), ("created_at", -1)])
            
            self.logger.info("✅ Índices criados para collections de transcrições e análises de imagem")
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao criar índices: {e}")
    
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
    
    def get_conversations_with_pending_images(self, limit: int = 100) -> List[Dict]:
        """Buscar conversas com imagens pendentes"""
        self._ensure_initialized()
        self._log_operation("busca de conversas com imagens pendentes", {"limit": limit})
        
        query = {
            # Excluir conversas já processadas
            "image_processing_status": {"$ne": "completed"},
            # Buscar conversas com imagens
            "$or": [
                {"image_messages": {"$gt": 0}},
                {"media_messages": {"$gt": 0}},
                {"contacts.messages.type": "image"},
                {"contacts.messages.media_type": "image"}
            ]
        }
        
        try:
            cursor = self.db.diarios.find(query).limit(limit)
            conversations = []
            
            for conv in cursor:
                # Verificar se realmente tem imagens pendentes
                has_pending_images = self._has_pending_images(conv)
                if has_pending_images:
                    conv["_id"] = str(conv["_id"])
                    conversations.append(conv)
            
            self._log_success("busca de conversas com imagens pendentes", {"encontradas": len(conversations)})
            return conversations
            
        except Exception as e:
            self._log_error("busca de conversas com imagens pendentes", e)
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
    
    def _has_pending_images(self, conversation: Dict) -> bool:
        """Verificar se a conversa tem imagens pendentes de processamento"""
        try:
            for contact in conversation.get('contacts', []):
                for message in contact.get('messages', []):
                    if self._is_image_message(message):
                        # Se não tem análise ou status não é completed
                        if (not message.get('image_analysis') and 
                            message.get('image_analysis_status') != 'completed'):
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
                    if (self._is_audio_message(message) and 
                        not self._has_transcription(message) and 
                        not self._is_download_failed(message)):
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
    
    def get_pending_images_for_conversation(self, conversation_id: str) -> List[Dict]:
        """Extrair imagens pendentes de uma conversa"""
        self._ensure_initialized()
        self._log_operation("extração de imagens pendentes", {"conversation_id": conversation_id})
        
        try:
            conversation = self.db.diarios.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return []
            
            pending_images = []
            contacts = conversation.get('contacts', [])
            
            for contact_idx, contact in enumerate(contacts):
                messages = contact.get('messages', [])
                
                for msg_idx, message in enumerate(messages):
                    if self._is_image_message(message) and not self._has_image_analysis(message):
                        image_info = self._create_image_info(
                            conversation_id, contact_idx, msg_idx, 
                            message, contact
                        )
                        pending_images.append(image_info)
            
            self._log_success("extração de imagens pendentes", {"encontradas": len(pending_images)})
            return pending_images
            
        except Exception as e:
            self._log_error("extração de imagens pendentes", e)
            return []
    
    def get_all_audios_for_conversation(self, conversation_id: str) -> List[Dict]:
        """Buscar TODOS os áudios de uma conversa (incluindo já transcritos)"""
        self._ensure_initialized()
        self._log_operation("busca de todos os áudios", {"conversation_id": conversation_id})
        
        try:
            conversation = self.db.diarios.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return []
            
            all_audios = []
            contacts = conversation.get('contacts', [])
            
            for contact_idx, contact in enumerate(contacts):
                messages = contact.get('messages', [])
                
                for msg_idx, message in enumerate(messages):
                    if self._is_audio_message(message):
                        audio_info = self._create_audio_info(
                            conversation_id, contact_idx, msg_idx, 
                            message, contact
                        )
                        all_audios.append(audio_info)
            
            self._log_success("extração de todos os áudios", {"encontrados": len(all_audios)})
            return all_audios
            
        except Exception as e:
            self._log_error("extração de todos os áudios", e)
            return []
    
    def mark_audio_download_failed(self, conversation_id: str, contact_idx: int, 
                                 message_idx: int, error_message: str) -> bool:
        """Marcar áudio como falha de download"""
        self._ensure_initialized()
        self._log_operation("marcar download falhado", {
            "conversation_id": conversation_id,
            "contact_idx": contact_idx,
            "message_idx": message_idx
        })
        
        try:
            # Atualizar mensagem com status de falha
            result = self.db.diarios.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        f"contacts.{contact_idx}.messages.{message_idx}.download_status": "failed",
                        f"contacts.{contact_idx}.messages.{message_idx}.download_error": error_message,
                        f"contacts.{contact_idx}.messages.{message_idx}.download_failed_at": datetime.now(),
                        f"contacts.{contact_idx}.messages.{message_idx}.404_error": "404" in error_message
                    }
                }
            )
            
            success = result.modified_count > 0
            self._log_success("marcar download falhado", {"modified": result.modified_count})
            return success
            
        except Exception as e:
            self._log_error("marcar download falhado", e)
            return False
    
    def get_all_images_for_conversation(self, conversation_id: str) -> List[Dict]:
        """Buscar TODAS as imagens de uma conversa (incluindo já analisadas)"""
        self._ensure_initialized()
        self._log_operation("busca de todas as imagens", {"conversation_id": conversation_id})
        
        try:
            conversation = self.db.diarios.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return []
            
            all_images = []
            contacts = conversation.get('contacts', [])
            
            for contact_idx, contact in enumerate(contacts):
                messages = contact.get('messages', [])
                
                for msg_idx, message in enumerate(messages):
                    if self._is_image_message(message):
                        image_info = self._create_image_info(
                            conversation_id, contact_idx, msg_idx, 
                            message, contact
                        )
                        all_images.append(image_info)
            
            self._log_success("extração de todas as imagens", {"encontradas": len(all_images)})
            return all_images
            
        except Exception as e:
            self._log_error("extração de todas as imagens", e)
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
    
    def _is_image_message(self, message: Dict) -> bool:
        """Verificar se mensagem é imagem"""
        return (
            message.get('media_type') == 'image' or
            message.get('is_image', False) or
            message.get('type') == 'image' or
            str(message.get('media_url', '')).endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')) or
            str(message.get('direct_media_url', '')).endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'))
        )
    
    def _has_transcription(self, message: Dict) -> bool:
        """Verificar se mensagem já tem transcrição"""
        return bool(
            message.get('audio_transcription') or
            message.get('transcription') or 
            message.get('transcription_text')
        )
    
    def _is_download_failed(self, message: Dict) -> bool:
        """Verificar se download falhou (404 ou erro)"""
        return bool(
            message.get('download_status') == 'failed' or
            message.get('download_error') or
            message.get('file_not_found') or
            message.get('404_error')
        )
    
    def _has_image_analysis(self, message: Dict) -> bool:
        """Verificar se mensagem já tem análise de imagem"""
        return bool(
            message.get('image_analysis') or
            message.get('image_description') or
            message.get('image_transcription')
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
    
    def _create_image_info(self, conversation_id: str, contact_idx: int, 
                          message_idx: int, message: Dict, contact: Dict) -> Dict:
        """Criar informações da imagem"""
        return {
            'conversation_id': conversation_id,
            'contact_idx': contact_idx,
            'message_idx': message_idx,
            'message_id': message.get('_id'),
            'contact_name': contact.get('contact_name', 'Desconhecido'),
            'file_url': self._get_image_url(message),
            'created_at': message.get('created_at'),
            'body': message.get('body', 'Imagem')
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
    
    def _get_image_url(self, message: Dict) -> Optional[str]:
        """Obter URL da imagem priorizando diferentes campos"""
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
    
    def update_image_analysis(self, conversation_id: str, contact_idx: int, 
                             message_idx: int, analysis: Dict) -> bool:
        """Atualizar análise de imagem"""
        self._log_operation("atualização de análise de imagem", {
            "conversation_id": conversation_id,
            "contact_idx": contact_idx,
            "message_idx": message_idx
        })
        
        try:
            result = self.db.diarios.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        f"contacts.{contact_idx}.messages.{message_idx}.image_analysis": analysis["description"],
                        f"contacts.{contact_idx}.messages.{message_idx}.image_analysis_data": analysis,
                        f"contacts.{contact_idx}.messages.{message_idx}.image_analysis_status": "completed",
                        f"contacts.{contact_idx}.messages.{message_idx}.analyzed_at": datetime.now(),
                        "updated_at": datetime.now()
                    }
                }
            )
            
            success = result.modified_count > 0
            
            # Verificar se todas as imagens da conversa foram processadas
            if success:
                self._check_and_update_image_conversation_status(conversation_id)
            
            self._log_success("atualização de análise de imagem", {"modified": result.modified_count})
            return success
            
        except Exception as e:
            self._log_error("atualização de análise de imagem", e)
            return False
    
    def save_image_analysis_to_collection(self, analysis_data: Dict) -> bool:
        """Salvar análise de imagem na collection dedicada"""
        self._ensure_initialized()
        
        try:
            # Preparar documento para a collection de análises de imagem
            analysis_doc = {
                "mensagem_id": analysis_data.get("mensagem_id"),
                "user_id": analysis_data.get("user_id"),
                "company_id": analysis_data.get("company_id"),
                "server_name": analysis_data.get("server_name"),
                "conversation_id": analysis_data.get("conversation_id"),
                "contact_name": analysis_data.get("contact_name"),
                "image_analysis": analysis_data.get("image_analysis", {}),
                "image_description": analysis_data.get("image_description"),
                "model": analysis_data.get("model"),
                "device": analysis_data.get("device"),
                "file_size": analysis_data.get("file_size"),
                "generation_time": analysis_data.get("generation_time"),
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # Inserir ou atualizar análise
            result = self.db.image_analyses.update_one(
                {"mensagem_id": analysis_doc["mensagem_id"]},
                {"$set": analysis_doc},
                upsert=True
            )
            
            self._log_success("salvamento na collection de análises de imagem", {
                "mensagem_id": analysis_doc["mensagem_id"],
                "modified": result.modified_count,
                "upserted": result.upserted_id is not None
            })
            
            return True
            
        except Exception as e:
            self._log_error("salvamento na collection de análises de imagem", e)
            return False
    
    def get_image_analysis_stats(self) -> Dict:
        """Obter estatísticas das análises de imagem"""
        self._ensure_initialized()
        
        try:
            total = self.db.image_analyses.count_documents({})
            
            # Estatísticas por usuário
            user_stats = list(self.db.image_analyses.aggregate([
                {"$group": {
                    "_id": "$user_id",
                    "count": {"$sum": 1},
                    "avg_generation_time": {"$avg": "$generation_time"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]))
            
            # Estatísticas por empresa
            company_stats = list(self.db.image_analyses.aggregate([
                {"$group": {
                    "_id": "$company_id",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]))
            
            return {
                "total_analyses": total,
                "top_users": user_stats,
                "top_companies": company_stats
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas de análises: {e}")
            return {
                "total_analyses": 0,
                "top_users": [],
                "top_companies": []
            }

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
    
    def _check_and_update_image_conversation_status(self, conversation_id: str):
        """Verificar se todas as imagens da conversa foram processadas e atualizar status"""
        try:
            # Buscar a conversa
            conversation = self.db.diarios.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return
            
            # Contar imagens pendentes
            total_images = 0
            processed_images = 0
            
            for contact in conversation.get('contacts', []):
                for message in contact.get('messages', []):
                    if self._is_image_message(message):
                        total_images += 1
                        if message.get('image_analysis_status') == 'completed':
                            processed_images += 1
            
            # Se todas as imagens foram processadas, marcar conversa como completa
            if total_images > 0 and processed_images == total_images:
                self.db.diarios.update_one(
                    {"_id": ObjectId(conversation_id)},
                    {
                        "$set": {
                            "image_processing_status": "completed",
                            "image_processing_completed_at": datetime.now(),
                            "image_processing_stats": {
                                "total_images": total_images,
                                "processed_images": processed_images,
                                "completion_date": datetime.now()
                            }
                        }
                    }
                )
                self.logger.info(f"✅ Conversa {conversation_id} marcada como processada: {processed_images}/{total_images} imagens")
            
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
                    # Incluir texto da mensagem, transcrição de áudio ou análise de imagem
                    message_text = self._get_message_content(message)
                    
                    if message_text:
                        message_type = self._get_message_type(message)
                        contact_data['messages'].append({
                            'timestamp': message.get('created_at'),
                            'text': message_text,
                            'message_type': message_type,
                            'original_type': message.get('type', message.get('media_type', 'text')),
                            'has_transcription': bool(message.get('audio_transcription')),
                            'has_image_analysis': bool(message.get('image_analysis'))
                        })
                
                conversation_text['contacts'].append(contact_data)
            
            # Adicionar histórico de mensagens dos últimos 7 dias
            conversation_text['historical_context'] = self._get_historical_messages(conversation_id)
            
            return conversation_text
            
        except Exception as e:
            self.logger.error(f"Erro ao obter texto da conversa: {e}")
            return {}
    
    def _get_message_content(self, message: Dict) -> str:
        """Obter conteúdo da mensagem priorizando transcrições e análises"""
        # Prioridade: transcrição de áudio > análise de imagem > texto original
        if message.get('audio_transcription'):
            return f"[ÁUDIO TRANSCRITO] {message.get('audio_transcription')}"
        
        if message.get('image_analysis'):
            analysis = message.get('image_analysis', {})
            if isinstance(analysis, dict):
                image_text = analysis.get('description', analysis.get('text', ''))
                if image_text:
                    return f"[IMAGEM ANALISADA] {image_text}"
        
        # Texto original da mensagem
        return message.get('body', '') or message.get('text', '')
    
    def _get_message_type(self, message: Dict) -> str:
        """Determinar tipo da mensagem"""
        if message.get('audio_transcription'):
            return 'audio_transcribed'
        if message.get('image_analysis'):
            return 'image_analyzed'
        if self._is_audio_message(message):
            return 'audio'
        if self._is_image_message(message):
            return 'image'
        return 'text'
    
    def _is_image_message(self, message: Dict) -> bool:
        """Verificar se mensagem é imagem"""
        return (
            message.get('media_type') == 'image' or
            message.get('is_image', False) or
            message.get('type') == 'image' or
            str(message.get('media_url', '')).endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')) or
            str(message.get('direct_media_url', '')).endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'))
        )
    
    def _get_historical_messages(self, conversation_id: str, days: int = 7) -> List[Dict]:
        """Buscar mensagens históricas dos últimos dias"""
        try:
            from datetime import datetime, timedelta
            
            # Calcular data limite
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Buscar conversas dos últimos 7 dias do mesmo usuário
            current_conversation = self.db.diarios.find_one({"_id": ObjectId(conversation_id)})
            if not current_conversation:
                return []
            
            user_name = current_conversation.get('user_name')
            if not user_name:
                return []
            
            # Buscar conversas do mesmo usuário nos últimos 7 dias
            historical_conversations = self.db.diarios.find({
                'user_name': user_name,
                'created_at': {
                    '$gte': start_date,
                    '$lt': end_date
                },
                '_id': {'$ne': ObjectId(conversation_id)}  # Excluir conversa atual
            }).sort('created_at', -1).limit(5)  # Máximo 5 conversas recentes
            
            historical_messages = []
            
            for conv in historical_conversations:
                conv_date = conv.get('created_at', conv.get('date_formatted', ''))
                
                # Extrair mensagens de cada contato
                for contact in conv.get('contacts', []):
                    contact_name = contact.get('contact_name', 'Desconhecido')
                    
                    for message in contact.get('messages', []):
                        message_content = self._get_message_content(message)
                        
                        if message_content:
                            historical_messages.append({
                                'conversation_id': str(conv['_id']),
                                'conversation_date': conv_date,
                                'contact_name': contact_name,
                                'timestamp': message.get('created_at'),
                                'text': message_content,
                                'message_type': self._get_message_type(message)
                            })
            
            # Ordenar por timestamp e limitar
            historical_messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return historical_messages[:50]  # Máximo 50 mensagens históricas
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar mensagens históricas: {e}")
            return []
    
    def save_conversation_analysis(self, conversation_id: str, analysis: Dict):
        """Salvar análise da conversa no MongoDB (DEPRECATED - usar save_diary_analysis_v2)"""
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
    
    def save_diary_analysis_v2(self, diary_id: str, analysis: Dict) -> bool:
        """Salvar análise do diário no novo formato (contact_analyses + diary_summary)"""
        self._ensure_initialized()
        try:
            # Preparar dados para o novo schema
            analysis_data = {
                'contact_analyses': analysis.get('contact_analyses', []),
                'diary_summary': analysis.get('diary_summary', {}),
                'analysis_stats': analysis.get('analysis_stats', {}),
                'analyzed_at': datetime.now(),
                'updated_at': datetime.now(),
                'analysis_version': 'v2'
            }
            
            result = self.db.diarios.update_one(
                {"_id": ObjectId(diary_id)},
                {"$set": analysis_data}
            )
            
            success = result.modified_count > 0
            self.logger.info(f"Análise v2 salva para diário {diary_id}: {success}")
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar análise v2: {e}")
            return False
    
    def get_diary_text_for_analysis_v2(self, diary_id: str) -> Optional[Dict]:
        """Buscar dados do diário para análise v2 (com contexto histórico)"""
        self._ensure_initialized()
        try:
            # Buscar diário
            diary = self.db.diarios.find_one({"_id": ObjectId(diary_id)})
            if not diary:
                return None
            
            # Adicionar contexto histórico
            historical_context = self._get_historical_messages(diary_id, days=7)
            
            # Preparar dados para análise
            analysis_data = {
                'diary_id': str(diary['_id']),
                'user_name': diary.get('user_name'),
                'company_name': diary.get('company_name'),
                'date': diary.get('date'),
                'date_formatted': diary.get('date_formatted'),
                'contacts': diary.get('contacts', []),
                'historical_context': historical_context
            }
            
            return analysis_data
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar dados do diário: {e}")
            return None
    
    def get_diaries_without_analysis_v2(self, limit: int = 100) -> List[Dict]:
        """Buscar diários sem análise v2"""
        self._ensure_initialized()
        try:
            query = {
                "$or": [
                    {"contact_analyses": {"$exists": False}},
                    {"analysis_version": {"$ne": "v2"}},
                    {"contact_analyses": {"$size": 0}}
                ]
            }
            
            cursor = self.db.diarios.find(query).limit(limit)
            diaries = []
            
            for diary in cursor:
                diary["_id"] = str(diary["_id"])
                diaries.append(diary)
            
            return diaries
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar diários sem análise v2: {e}")
            return []
    
    def get_diary_analysis_stats_v2(self) -> Dict:
        """Obter estatísticas das análises v2"""
        self._ensure_initialized()
        try:
            total_diaries = self.db.diarios.count_documents({})
            analyzed_diaries = self.db.diaries.count_documents({
                "contact_analyses": {"$exists": True, "$ne": []},
                "analysis_version": "v2"
            })
            
            # Estatísticas por empresa
            company_stats = list(self.db.diarios.aggregate([
                {"$match": {"analysis_version": "v2"}},
                {"$group": {
                    "_id": "$company_name",
                    "analyzed_diaries": {"$sum": 1},
                    "total_contacts": {"$sum": {"$size": {"$ifNull": ["$contact_analyses", []]}}}
                }},
                {"$sort": {"analyzed_diaries": -1}}
            ]))
            
            return {
                'total_diaries': total_diaries,
                'analyzed_diaries': analyzed_diaries,
                'pending_diaries': total_diaries - analyzed_diaries,
                'analysis_rate': (analyzed_diaries / total_diaries * 100) if total_diaries > 0 else 0,
                'company_stats': company_stats
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas v2: {e}")
            return {}
    
    def save_transcription_to_collection(self, transcription_data: Dict) -> bool:
        """Salvar transcrição na collection dedicada"""
        self._ensure_initialized()
        
        try:
            # Preparar documento para a collection de transcrições
            transcription_doc = {
                "mensagem_id": transcription_data.get("mensagem_id"),
                "user_id": transcription_data.get("user_id"),
                "company_id": transcription_data.get("company_id"),
                "server_name": transcription_data.get("server_name"),
                "conversation_id": transcription_data.get("conversation_id"),
                "contact_name": transcription_data.get("contact_name"),
                "transcription": transcription_data.get("transcription", {}),
                "audio_duration": transcription_data.get("audio_duration"),
                "confidence": transcription_data.get("confidence"),
                "whisper_model": transcription_data.get("whisper_model"),
                "device": transcription_data.get("device"),
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # Inserir ou atualizar transcrição
            result = self.db.transcriptions.update_one(
                {"mensagem_id": transcription_doc["mensagem_id"]},
                {"$set": transcription_doc},
                upsert=True
            )
            
            self._log_success("salvamento na collection de transcrições", {
                "mensagem_id": transcription_doc["mensagem_id"],
                "upserted": result.upserted_id is not None,
                "modified": result.modified_count
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar transcrição na collection: {e}")
            return False
    
    def get_transcriptions_by_user(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Buscar transcrições por usuário"""
        self._ensure_initialized()
        
        try:
            cursor = self.db.transcriptions.find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar transcrições por usuário: {e}")
            return []
    
    def get_transcriptions_by_company(self, company_id: str, limit: int = 100) -> List[Dict]:
        """Buscar transcrições por empresa"""
        self._ensure_initialized()
        
        try:
            cursor = self.db.transcriptions.find(
                {"company_id": company_id}
            ).sort("created_at", -1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar transcrições por empresa: {e}")
            return []
    
    def search_transcriptions(self, query: Dict, limit: int = 100) -> List[Dict]:
        """Buscar transcrições com filtros personalizados"""
        self._ensure_initialized()
        
        try:
            cursor = self.db.transcriptions.find(query).sort("created_at", -1).limit(limit)
            return list(cursor)
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar transcrições: {e}")
            return []
    
    def get_transcription_stats(self) -> Dict:
        """Obter estatísticas das transcrições"""
        self._ensure_initialized()
        
        try:
            total = self.db.transcriptions.count_documents({})
            
            # Estatísticas por usuário
            user_stats = list(self.db.transcriptions.aggregate([
                {"$group": {
                    "_id": "$user_id",
                    "count": {"$sum": 1},
                    "avg_confidence": {"$avg": "$confidence"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]))
            
            # Estatísticas por empresa
            company_stats = list(self.db.transcriptions.aggregate([
                {"$group": {
                    "_id": "$company_id",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]))
            
            return {
                "total_transcriptions": total,
                "top_users": user_stats,
                "top_companies": company_stats
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
    
    def _cleanup(self):
        """Fechar conexão MongoDB"""
        if hasattr(self, 'client'):
            self.client.close()
