"""
Configuração centralizada do sistema
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class Config:
    """Configurações do sistema"""
    
    # MongoDB
    MONGODB_URI = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "dashboard_whatsapp")
    
    # Whisper
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
    WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "pt")
    
    # GPU Settings
    GPU_BATCH_SIZE = int(os.getenv("GPU_BATCH_SIZE", "4"))
    GPU_MEMORY_FRACTION = float(os.getenv("GPU_MEMORY_FRACTION", "0.8"))
    
    # Processing
    MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "8"))
    AUDIO_DOWNLOAD_TIMEOUT = int(os.getenv("AUDIO_DOWNLOAD_TIMEOUT", "60"))
    
    # Ollama
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    AUDIO_DIR = BASE_DIR / "audio_files"
    DOWNLOADS_DIR = BASE_DIR / "downloads"
    TRANSCRIPTIONS_DIR = BASE_DIR / "transcriptions"
    TEMP_DIR = BASE_DIR / "temp"
    LOGS_DIR = BASE_DIR / "logs"
    MODELS_DIR = BASE_DIR / "models"
    
    # Create directories
    for dir_path in [AUDIO_DIR, DOWNLOADS_DIR, TRANSCRIPTIONS_DIR, TEMP_DIR, LOGS_DIR, MODELS_DIR]:
        dir_path.mkdir(exist_ok=True)
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"