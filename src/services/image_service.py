"""
Service para análise e descrição de imagens com modelos de visão computacional
"""
import torch
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO

from .base_service import BaseService
from ..config import Config

class ImageService(BaseService):
    """Service para análise e descrição de imagens"""
    
    def _initialize(self):
        """Inicializar modelo de visão computacional"""
        self.device = self._setup_gpu()
        self.model = None
        self.processor = None
        self._load_vision_model()
    
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
    
    def _load_vision_model(self):
        """Carregar modelo de visão computacional"""
        try:
            from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
            
            self.logger.info("📥 Carregando modelo LLaVA 1.6...")
            
            # Usar LLaVA 1.6 - modelo mais recente e eficiente
            model_name = "llava-hf/llava-v1.6-mistral-7b-hf"
            
            self.processor = LlavaNextProcessor.from_pretrained(
                model_name,
                cache_dir=str(Config.MODELS_DIR)
            )
            
            self.model = LlavaNextForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                cache_dir=str(Config.MODELS_DIR),
                low_cpu_mem_usage=True
            )
            
            if not torch.cuda.is_available():
                self.model = self.model.to(self.device)
            
            self.logger.info("✅ Modelo LLaVA 1.6 carregado")
            
        except ImportError:
            self.logger.error("❌ Dependências não instaladas. Execute: pip install transformers torch torchvision pillow")
            raise
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar modelo: {e}")
            raise
    
    def analyze_image(self, image_path: str, prompt: str = "Descreva esta imagem em detalhes em português") -> Optional[Dict]:
        """Analisar e descrever uma imagem"""
        self._ensure_initialized()
        self._log_operation("análise de imagem", {"image_path": image_path, "prompt": prompt})
        
        try:
            # Carregar imagem
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
            
            # Preparar prompt simples
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            # Processar imagem e texto
            try:
                inputs = self.processor.apply_chat_template(
                    messages,
                    tokenize=True,
                    add_generation_prompt=True,
                    return_tensors="pt"
                )
                
                if inputs is None:
                    self.logger.error("Falha ao processar template de conversa")
                    return None
                
                # Processar imagem
                image_inputs = self.processor(images=image, return_tensors="pt")
                
                # Mover para device
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                image_inputs = {k: v.to(self.device) for k, v in image_inputs.items()}
                
                # Gerar descrição
                start_time = time.time()
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        **image_inputs,
                        max_new_tokens=512,
                        do_sample=False,
                        temperature=0.2,
                        use_cache=True
                    )
                
                generation_time = time.time() - start_time
                
                # Decodificar resposta
                if 'input_ids' in inputs and len(outputs) > 0:
                    generated_text = self.processor.decode(
                        outputs[0][inputs['input_ids'].shape[1]:], 
                        skip_special_tokens=True
                    )
                else:
                    self.logger.error("Falha ao decodificar resposta do modelo")
                    return None
                
            except Exception as e:
                self.logger.error(f"Erro no processamento do modelo: {e}")
                return None
            
            # Preparar resultado
            result = {
                'description': generated_text.strip(),
                'prompt_used': prompt,
                'image_path': image_path,
                'image_size': image.size,
                'generation_time': generation_time,
                'model': 'llava-v1.6-mistral-7b',
                'device': self.device,
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
        batch_size = Config.GPU_BATCH_SIZE
        
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i + batch_size]
            batch_results = self._analyze_batch_gpu(batch, prompt)
            results.extend(batch_results)
        
        successful = len([r for r in results if r is not None])
        self._log_success("análise em batch", {
            "total": len(image_paths),
            "successful": successful,
            "failed": len(image_paths) - successful
        })
        
        return results
    
    def _analyze_batch_gpu(self, image_paths: List[str], prompt: str) -> List[Optional[Dict]]:
        """Analisar batch na GPU"""
        results = []
        
        for image_path in image_paths:
            try:
                result = self.analyze_image(image_path, prompt)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Erro na análise de {image_path}: {e}")
                results.append(None)
        
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
        """Salvar análise em arquivo JSON no mesmo padrão dos downloads"""
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
                "model": "llava-v1.6-mistral-7b",
                "device": self.device
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
