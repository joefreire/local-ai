"""
Service para download de arquivos de áudio
"""
import requests
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_service import BaseService
from ..config import Config

class DownloadService(BaseService):
    """Service para download de arquivos"""
    
    def _initialize(self):
        """Inicializar service"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Desabilitar verificação SSL para URLs internas
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def download_audio_batch(self, audio_urls: List[Dict]) -> List[Tuple[Dict, Optional[str]]]:
        """Baixar múltiplos áudios em paralelo"""
        self._log_operation("download em batch", {"count": len(audio_urls)})
        
        results = []
        
        with ThreadPoolExecutor(max_workers=Config.MAX_CONCURRENT_JOBS) as executor:
            future_to_audio = {
                executor.submit(self._download_single, audio_info): audio_info 
                for audio_info in audio_urls
            }
            
            for future in as_completed(future_to_audio):
                result = future.result()
                results.append(result)
        
        successful = len([r for r in results if r[1] is not None])
        self._log_success("download em batch", {
            "total": len(audio_urls),
            "successful": successful,
            "failed": len(audio_urls) - successful
        })
        
        return results
    
    def _download_single(self, audio_info: Dict) -> Tuple[Dict, Optional[str]]:
        """Baixar um único áudio"""
        try:
            file_path = self.download_audio_file(
                audio_info['conversation_id'],
                audio_info['message_id'],
                audio_info['file_url']
            )
            return audio_info, file_path
        except Exception as e:
            self.logger.error(f"Erro ao baixar {audio_info['message_id']}: {e}")
            return audio_info, None
    
    def download_audio_file(self, conversation_id: str, message_id: str, url: str) -> Optional[str]:
        """Baixar arquivo de áudio"""
        self._ensure_initialized()
        self._log_operation("download de arquivo", {
            "conversation_id": conversation_id,
            "message_id": message_id
        })
        
        try:
            # Criar diretório da conversa
            conv_dir = Config.DOWNLOADS_DIR / conversation_id
            conv_dir.mkdir(exist_ok=True)
            
            # Determinar extensão
            extension = self._get_file_extension(url)
            
            # Caminho do arquivo
            file_path = conv_dir / f"{message_id}{extension}"
            
            # Se já existe, retornar
            if file_path.exists():
                self.logger.info(f"Arquivo já existe: {file_path.name}")
                return str(file_path)
            
            # Download
            if url.startswith('http'):
                self._download_from_url(url, file_path)
            else:
                self._copy_local_file(url, file_path)
            
            self._log_success("download de arquivo", {"file_path": str(file_path)})
            return str(file_path)
            
        except Exception as e:
            self._log_error("download de arquivo", e)
            return None
    
    def download_media_file(self, conversation_id: str, message_id: str, url: str, media_type: str = 'audio') -> Optional[str]:
        """Baixar arquivo de mídia (áudio ou imagem)"""
        if media_type == 'audio':
            return self.download_audio_file(conversation_id, message_id, url)
        elif media_type == 'image':
            return self.download_image_file(conversation_id, message_id, url)
        else:
            self.logger.error(f"Tipo de mídia não suportado: {media_type}")
            return None
    
    def download_image_file(self, conversation_id: str, message_id: str, url: str) -> Optional[str]:
        """Baixar arquivo de imagem"""
        self._ensure_initialized()
        self._log_operation("download de imagem", {
            "conversation_id": conversation_id,
            "message_id": message_id
        })
        
        try:
            # Criar diretório da conversa
            conv_dir = Config.DOWNLOADS_DIR / conversation_id
            conv_dir.mkdir(exist_ok=True)
            
            # Determinar extensão
            extension = self._get_image_extension(url)
            
            # Caminho do arquivo
            file_path = conv_dir / f"{message_id}{extension}"
            
            # Se já existe, retornar
            if file_path.exists():
                self.logger.info(f"Imagem já existe: {file_path.name}")
                return str(file_path)
            
            # Download
            if url.startswith('http'):
                self._download_from_url(url, file_path)
            else:
                self._copy_local_file(url, file_path)
            
            self._log_success("download de imagem", {"file_path": str(file_path)})
            return str(file_path)
            
        except Exception as e:
            self._log_error("download de imagem", e)
            return None
    
    def _get_file_extension(self, url: str) -> str:
        """Determinar extensão do arquivo"""
        if not url:
            return ".oga"  # Padrão WhatsApp
        
        for ext in ['.mp3', '.wav', '.ogg', '.m4a', '.oga']:
            if ext in url.lower():
                return ext
        
        return ".oga"  # Padrão
    
    def _get_image_extension(self, url: str) -> str:
        """Determinar extensão da imagem"""
        if not url:
            return ".jpg"  # Padrão
        
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']:
            if ext in url.lower():
                return ext
        
        return ".jpg"  # Padrão
    
    def _download_from_url(self, url: str, file_path: Path):
        """Baixar arquivo de URL"""
        try:
            response = self.session.get(url, stream=True, timeout=Config.AUDIO_DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise FileNotFoundError(f"404 Client Error: Not Found for url: {url}")
            else:
                raise
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Erro de conexão: {e}")
    
    def _copy_local_file(self, source_path: str, dest_path: Path):
        """Copiar arquivo local"""
        if not Path(source_path).exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {source_path}")
        
        shutil.copy2(source_path, dest_path)
    
    def get_download_stats(self) -> Dict[str, int]:
        """Obter estatísticas de downloads"""
        total_files = 0
        total_size = 0
        
        if Config.DOWNLOADS_DIR.exists():
            for file_path in Config.DOWNLOADS_DIR.rglob("*"):
                if file_path.is_file() and not file_path.name.endswith('.json'):
                    total_files += 1
                    total_size += file_path.stat().st_size
        
        return {
            "total_files": total_files,
            "total_size_mb": total_size / (1024 * 1024),
            "downloads_dir": str(Config.DOWNLOADS_DIR)
        }
    
    def cleanup_downloads(self, conversation_id: Optional[str] = None) -> bool:
        """Limpar downloads"""
        try:
            if conversation_id:
                conv_dir = Config.DOWNLOADS_DIR / conversation_id
                if conv_dir.exists():
                    shutil.rmtree(conv_dir)
                    self.logger.info(f"Downloads limpos para conversa: {conversation_id}")
            else:
                if Config.DOWNLOADS_DIR.exists():
                    shutil.rmtree(Config.DOWNLOADS_DIR)
                    Config.DOWNLOADS_DIR.mkdir(exist_ok=True)
                    self.logger.info("Todos os downloads limpos")
            
            return True
        except Exception as e:
            self._log_error("limpeza de downloads", e)
            return False
    
    def _cleanup(self):
        """Fechar sessão"""
        if hasattr(self, 'session'):
            self.session.close()
