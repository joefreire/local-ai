"""
Service base com funcionalidades comuns
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

class BaseService(ABC):
    """Classe base para todos os services"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False
    
    def _ensure_initialized(self):
        """Garantir que o service foi inicializado"""
        if not self._initialized:
            self._initialize()
            self._initialized = True
    
    @abstractmethod
    def _initialize(self):
        """Inicializar o service"""
        pass
    
    def _log_operation(self, operation: str, details: Optional[Dict[str, Any]] = None):
        """Log padronizado para operações"""
        message = f"Executando {operation}"
        if details:
            message += f" - {details}"
        self.logger.info(message)
    
    def _log_success(self, operation: str, result: Optional[Dict[str, Any]] = None):
        """Log de sucesso"""
        message = f"✅ {operation} concluído com sucesso"
        if result:
            message += f" - {result}"
        self.logger.info(message)
    
    def _log_error(self, operation: str, error: Exception):
        """Log de erro"""
        self.logger.error(f"❌ Erro em {operation}: {str(error)}")
    
    def close(self):
        """Fechar recursos do service"""
        if self._initialized:
            self._cleanup()
            self._initialized = False
    
    def _cleanup(self):
        """Limpeza de recursos (implementar se necessário)"""
        pass
