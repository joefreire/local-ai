#!/usr/bin/env python3
"""
Transcritor ultra-simples usando PyMongo síncrono
Comando único para transcrever áudios do MongoDB usando Whisper
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import pymongo
import requests
import tempfile
import shutil
import whisper
import json
from bson import ObjectId
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class UltraSimpleTranscriber:
    """Transcritor ultra-simples"""
    
    def __init__(self):
        # MongoDB - usar mesmas variáveis do check_pending.py
        mongodb_uri = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        mongodb_db = os.getenv("MONGODB_DATABASE", "dashboard_whatsapp")
        
        self.client = pymongo.MongoClient(mongodb_uri)
        self.db = self.client[mongodb_db]
        
        # Diretórios organizados por ID
        self.base_dir = Path.cwd()
        self.downloads_dir = self.base_dir / "downloads"
        self.logs_dir = self.base_dir / "logs" 
        self.temp_dir = self.base_dir / "temp"
        
        # Criar diretórios se não existem
        self.downloads_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Whisper (carrega apenas quando necessário)
        self.model = None
    
    def load_whisper_model(self):
        """Carregar modelo Whisper apenas quando necessário"""
        if self.model is None:
            logger.info("📥 Carregando modelo Whisper turbo...")
            self.model = whisper.load_model("turbo")
            logger.info("✅ Modelo carregado")
        return self.model

    def find_pending_diarios(self, limit: int = 5):
        """Buscar diários com áudios pendentes"""
        query = {
            "$or": [
                {"audio_messages": {"$gt": 0}},
                {"media_messages": {"$gt": 0}}
            ],
            "status_audios": {"$in": ["pending", "error"]}
        }
        
        diarios = list(self.db.diarios.find(query).limit(limit))
        
        for diario in diarios:
            diario["_id"] = str(diario["_id"])
        
        logger.info(f"📋 Encontrados {len(diarios)} diários pendentes")
        return diarios

    def extract_audio_urls(self, diario):
        """Extrair URLs de áudio baseado na estrutura real do MongoDB"""
        audio_messages = []
        contacts = diario.get('contacts', [])
        
        for contact_idx, contact in enumerate(contacts):
            messages = contact.get('messages', [])
            
            for msg_idx, message in enumerate(messages):
                # Verificar se é áudio baseado na estrutura real
                is_audio = (
                    message.get('media_type') == 'audio' or
                    message.get('is_audio', False) or
                    message.get('type') == 'audio' or
                    str(message.get('media_url', '')).endswith(('.mp3', '.wav', '.ogg', '.m4a', '.oga')) or
                    str(message.get('direct_media_url', '')).endswith(('.mp3', '.wav', '.ogg', '.m4a', '.oga'))
                )
                
                # Verificar se já foi transcrito
                has_transcription = (
                    message.get('audio_transcription') or
                    message.get('transcription') or 
                    message.get('transcription_text')
                )
                
                if is_audio and not has_transcription:
                    # Priorizar direct_media_url, depois download_url, depois media_url
                    file_url = (
                        message.get('direct_media_url') or 
                        message.get('download_url') or 
                        message.get('media_url') or
                        message.get('file_url') or
                        message.get('file_path')
                    )
                    
                    if file_url:
                        audio_messages.append({
                            'contact_idx': contact_idx,
                            'message_idx': msg_idx,
                            'file_url': file_url,
                            'message_id': message.get('_id', f"{contact_idx}_{msg_idx}"),
                            'contact_name': contact.get('contact_name', 'Desconhecido'),
                            'created_at': message.get('created_at', ''),
                            'body': message.get('body', 'Áudio')
                        })
        
        return audio_messages

    def get_diario_dir(self, diario_id: str):
        """Obter diretório do diário"""
        diario_dir = self.downloads_dir / diario_id
        diario_dir.mkdir(exist_ok=True)
        return diario_dir
    
    def download_audio(self, diario_id: str, message_id: str, url: str):
        """Baixar áudio organizadamente"""
        try:
            # Criar diretório do diário
            diario_dir = self.get_diario_dir(diario_id)
            
            # Determinar extensão do arquivo
            extension = ".oga"  # Padrão WhatsApp
            if url:
                for ext in ['.mp3', '.wav', '.ogg', '.m4a', '.oga']:
                    if ext in url.lower():
                        extension = ext
                        break
            
            # Nome do arquivo: message_id + extensão
            filename = f"{message_id}{extension}"
            file_path = diario_dir / filename
            
            # Se já existe, não baixar novamente
            if file_path.exists():
                logger.info(f"📂 Arquivo já existe: {filename}")
                return str(file_path)
            
            # Download
            if url.startswith('http'):
                logger.info(f"⬇️ Baixando: {filename}")
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                if Path(url).exists():
                    logger.info(f"📂 Copiando: {filename}")
                    shutil.copy2(url, file_path)
                else:
                    raise FileNotFoundError(f"Arquivo não encontrado: {url}")
            
            logger.info(f"✅ Baixado: {filename}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ Erro ao baixar {url}: {e}")
            return None

    def save_transcription_file(self, diario_id: str, message_id: str, transcription: dict):
        """Salvar transcrição como arquivo JSON"""
        try:
            diario_dir = self.get_diario_dir(diario_id)
            transcription_file = diario_dir / f"{message_id}_transcription.json"
            
            with open(transcription_file, 'w', encoding='utf-8') as f:
                json.dump(transcription, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Transcrição salva: {message_id}_transcription.json")
            return str(transcription_file)
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar transcrição: {e}")
            return None
    
    def load_transcription_file(self, diario_id: str, message_id: str):
        """Carregar transcrição de arquivo JSON"""
        try:
            diario_dir = self.get_diario_dir(diario_id)
            transcription_file = diario_dir / f"{message_id}_transcription.json"
            
            if transcription_file.exists():
                with open(transcription_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar transcrição: {e}")
            return None

    def transcribe_file(self, file_path: str):
        """Transcrever arquivo"""
        try:
            logger.info(f"🎙️ Transcrevendo {Path(file_path).name}")
            
            # Carregar modelo se necessário
            model = self.load_whisper_model()
            
            result = model.transcribe(file_path, language="pt")
            
            return {
                "text": result["text"].strip(),
                "segments": result.get("segments", []),
                "language": result.get("language", "pt"),
                "file_path": file_path,
                "transcribed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na transcrição: {e}")
            return None

    def download_only(self, limit: int = 5):
        """Apenas baixar áudios sem transcrever"""
        logger.info(f"⬇️ Iniciando download de áudios de até {limit} diários")
        
        diarios = self.find_pending_diarios(limit)
        if not diarios:
            logger.info("📭 Nenhum diário pendente")
            return []
        
        results = []
        for diario in diarios:
            diario_id = diario["_id"]
            user_name = diario.get("user_name", "Desconhecido")
            
            logger.info(f"📥 Baixando áudios: {diario_id} - {user_name}")
            
            audio_messages = self.extract_audio_urls(diario)
            if not audio_messages:
                logger.info("📭 Nenhum áudio pendente")
                continue
            
            downloaded = 0
            for audio_info in audio_messages:
                message_id = audio_info['message_id']
                file_path = self.download_audio(
                    diario_id, 
                    message_id, 
                    audio_info['file_url']
                )
                if file_path:
                    downloaded += 1
            
            results.append({
                'diario_id': diario_id,
                'total': len(audio_messages),
                'downloaded': downloaded
            })
        
        return results

    def close(self):
        """Fechar conexões"""
        self.client.close()


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Transcrever áudios pendentes")
    parser.add_argument("--limit", type=int, default=3, help="Limite de diários")
    parser.add_argument("--download-only", action="store_true", help="Apenas baixar áudios")
    
    args = parser.parse_args()
    
    print("🎙️ Transcritor Ultra-Simples de Áudios")
    print("=" * 50)
    print(f"📊 Limite: {args.limit} diários")
    print(f"🔗 MongoDB: {os.getenv('MONGODB_URL', 'localhost')}")
    print()
    
    transcriber = UltraSimpleTranscriber()
    
    try:
        if args.download_only:
            print("⬇️ MODO: Apenas Download")
            results = transcriber.download_only(args.limit)
            
            print(f"\n📥 DOWNLOAD CONCLUÍDO!")
            print("=" * 50)
            for result in results:
                diario_id = result['diario_id'][:8]
                downloaded = result['downloaded']
                total = result['total']
                print(f"📁 {diario_id}: {downloaded}/{total} áudios baixados")
        else:
            print("🚀 MODO: Processamento Completo")
            print("💡 Use --download-only para apenas baixar")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 Interrompido pelo usuário")
        return 1
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return 1
        
    finally:
        transcriber.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)