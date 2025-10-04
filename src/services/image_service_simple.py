"""
Service simplificado para análise de imagens usando Ollama
"""
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from PIL import Image
import base64
from io import BytesIO

from .base_service import BaseService
from ..config import Config

class ImageServiceSimple(BaseService):
    """Service simplificado para análise de imagens usando Ollama"""
    
    def _initialize(self):
        """Inicializar serviço"""
        self.ollama_url = Config.OLLAMA_BASE_URL
        self.model_name = "llava:7b"  # Modelo mais leve e estável
        self._check_ollama_connection()
    
    def _check_ollama_connection(self):
        """Verificar conexão com Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self.logger.info("✅ Conexão com Ollama estabelecida")
                
                # Verificar se o modelo está disponível
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                if self.model_name in model_names:
                    self.logger.info(f"✅ Modelo {self.model_name} disponível")
                else:
                    self.logger.warning(f"⚠️ Modelo {self.model_name} não encontrado")
                    self.logger.info("💡 Modelos disponíveis: " + ", ".join(model_names))
            else:
                self.logger.error("❌ Falha na conexão com Ollama")
        except Exception as e:
            self.logger.error(f"❌ Erro ao conectar com Ollama: {e}")
    
    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Codificar imagem para base64"""
        try:
            if image_path.startswith('http'):
                # Download de URL
                response = requests.get(image_path)
                image = Image.open(BytesIO(response.content))
            else:
                # Arquivo local
                if not Path(image_path).exists():
                    self.logger.error(f"Imagem não encontrada: {image_path}")
                    return None
                image = Image.open(image_path)
            
            # Converter para RGB se necessário
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Redimensionar se muito grande
            max_size = 1024
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Codificar para base64
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return img_base64
            
        except Exception as e:
            self.logger.error(f"Erro ao codificar imagem: {e}")
            return None
    
    def analyze_image(self, image_path: str, prompt: str = "Descreva esta imagem em detalhes em português") -> Optional[Dict]:
        """Analisar e descrever uma imagem usando Ollama"""
        self._ensure_initialized()
        self._log_operation("análise de imagem", {"image_path": image_path, "prompt": prompt})
        
        try:
            # Codificar imagem
            img_base64 = self._encode_image_to_base64(image_path)
            if not img_base64:
                return None
            
            # Preparar payload para Ollama
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "images": [img_base64],
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_tokens": 512
                }
            }
            
            # Enviar requisição
            start_time = time.time()
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=120
            )
            generation_time = time.time() - start_time
            
            if response.status_code != 200:
                self.logger.error(f"Erro na requisição Ollama: {response.status_code}")
                return None
            
            # Processar resposta
            result_data = response.json()
            description = result_data.get('response', '').strip()
            
            if not description:
                self.logger.error("Resposta vazia do modelo")
                return None
            
            # Preparar resultado
            result = {
                'description': description,
                'prompt_used': prompt,
                'image_path': image_path,
                'generation_time': generation_time,
                'model': self.model_name,
                'analyzed_at': datetime.now().isoformat()
            }
            
            self._log_success("análise de imagem", {
                "description_length": len(result['description']),
                "generation_time": generation_time
            })
            
            return result
            
        except Exception as e:
            self._log_error("análise de imagem", e)
            return None
    
    def analyze_image_batch(self, image_paths: List[str], prompt: str = "Descreva esta imagem em detalhes em português") -> List[Optional[Dict]]:
        """Analisar múltiplas imagens em batch"""
        self._log_operation("análise em batch", {"image_count": len(image_paths), "prompt": prompt})
        
        results = []
        
        for i, image_path in enumerate(image_paths, 1):
            self.logger.info(f"Processando imagem {i}/{len(image_paths)}: {Path(image_path).name}")
            result = self.analyze_image(image_path, prompt)
            results.append(result)
        
        successful = len([r for r in results if r is not None])
        self._log_success("análise em batch", {
            "total": len(image_paths),
            "successful": successful,
            "failed": len(image_paths) - successful
        })
        
        return results
    
    def extract_text_from_image(self, image_path: str) -> Optional[Dict]:
        """Extrair texto de uma imagem (OCR)"""
        self._ensure_initialized()
        self._log_operation("extração de texto", {"image_path": image_path})
        
        try:
            # Usar prompt específico para OCR
            ocr_prompt = "Extraia todo o texto visível nesta imagem. Retorne apenas o texto encontrado, sem explicações adicionais."
            
            result = self.analyze_image(image_path, ocr_prompt)
            
            if result:
                result['extraction_type'] = 'OCR'
                result['prompt_used'] = ocr_prompt
            
            return result
            
        except Exception as e:
            self._log_error("extração de texto", e)
            return None
    
    def test_image_analysis(self, image_path: str) -> bool:
        """Testar análise de imagem"""
        self.logger.info(f"🧪 Testando análise de imagem: {image_path}")
        
        try:
            result = self.analyze_image(image_path)
            if result:
                self.logger.info(f"✅ Teste OK - Descrição: {result['description'][:100]}...")
                return True
            else:
                self.logger.error("❌ Teste falhou")
                return False
        except Exception as e:
            self.logger.error(f"❌ Erro no teste: {e}")
            return False
    
    def save_analysis_to_json(self, conversation_id: str, message_id: str, 
                             analysis_data: Dict) -> Optional[str]:
        """Salvar análise em arquivo JSON"""
        self._ensure_initialized()
        
        try:
            # Criar diretório da conversa
            conv_dir = Config.TRANSCRIPTIONS_DIR / conversation_id
            conv_dir.mkdir(exist_ok=True)
            
            # Caminho do arquivo JSON
            json_path = conv_dir / f"{message_id}_image_analysis.json"
            
            # Se já existe, retornar
            if json_path.exists():
                self.logger.info(f"Análise já existe: {json_path.name}")
                return str(json_path)
            
            # Preparar dados para salvar
            save_data = {
                "conversation_id": conversation_id,
                "message_id": message_id,
                "analysis": analysis_data,
                "created_at": datetime.now().isoformat(),
                "model": self.model_name,
                "service": "ollama"
            }
            
            # Salvar JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ Análise salva: {json_path.name}")
            return str(json_path)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar análise: {e}")
            return None
    
    def load_analysis_from_json(self, conversation_id: str, message_id: str) -> Optional[Dict]:
        """Carregar análise de arquivo JSON"""
        self._ensure_initialized()
        
        try:
            json_path = Config.TRANSCRIPTIONS_DIR / conversation_id / f"{message_id}_image_analysis.json"
            
            if not json_path.exists():
                return None
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('analysis')
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar análise: {e}")
            return None
