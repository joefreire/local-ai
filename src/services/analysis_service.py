"""
Service para interação com Llama/Ollama
"""
import requests
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_service import BaseService
from ..config import Config

class LlamaService(BaseService):
    """Service para interação com Llama via Ollama"""
    
    def _initialize(self):
        """Inicializar service"""
        self.base_url = Config.OLLAMA_BASE_URL
        self.model = Config.OLLAMA_MODEL
        self._test_connection()
    
    def _test_connection(self):
        """Testar conexão com Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            if self.model in model_names:
                self.logger.info(f"✅ Ollama conectado - Modelo {self.model} disponível")
            else:
                self.logger.warning(f"⚠️ Modelo {self.model} não encontrado")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Ollama não disponível: {e}")
    
    def analyze_conversation(self, conversation_data: Dict) -> Dict:
        """Analisar conversa completa"""
        self._log_operation("análise de conversa", {
            "conversation_id": conversation_data.get('conversation_id')
        })
        
        try:
            if not conversation_data or not conversation_data.get('contacts'):
                return {'error': 'Dados de conversa inválidos'}
            
            # Preparar texto da conversa
            conversation_text = self._prepare_conversation_text(conversation_data)
            
            if not conversation_text.strip():
                return {'error': 'Conversa sem conteúdo para análise'}
            
            # Análise completa com prompts
            analysis = {
                'summary': self._generate_summary_with_prompt(conversation_text),
                'topics': self._extract_topics_with_prompt(conversation_text),
                'sentiment': self._analyze_sentiment_with_prompt(conversation_text),
                'insights': self._generate_insights_with_prompt(conversation_text),
                'conversation_stats': self._calculate_stats(conversation_data),
                'analyzed_at': datetime.now().isoformat()
            }
            
            self._log_success("análise de conversa", {
                "conversation_id": conversation_data.get('conversation_id'),
                "topics_count": len(analysis['topics']['result']) if isinstance(analysis['topics'], dict) else len(analysis['topics']),
                "insights_count": len(analysis['insights']['result']) if isinstance(analysis['insights'], dict) else len(analysis['insights'])
            })
            
            return analysis
            
        except Exception as e:
            self._log_error("análise de conversa", e)
            return {'error': str(e)}
    
    def _prepare_conversation_text(self, conversation_data: Dict) -> str:
        """Preparar texto da conversa para análise"""
        text_parts = []
        
        for contact in conversation_data.get('contacts', []):
            contact_name = contact.get('contact_name', 'Desconhecido')
            text_parts.append(f"\n=== Conversa com {contact_name} ===")
            
            for message in contact.get('messages', []):
                message_text = (
                    message.get('audio_transcription') or 
                    message.get('body', '') or 
                    message.get('text', '')
                )
                
                if message_text:
                    timestamp = message.get('timestamp', '')
                    message_type = message.get('message_type', 'text')
                    
                    prefix = f"[{timestamp}] {contact_name}: " if timestamp else f"{contact_name}: "
                    if message_type == 'audio':
                        prefix += "[ÁUDIO] "
                    
                    text_parts.append(f"{prefix}{message_text}")
        
        return "\n".join(text_parts)
    
    def _generate_summary(self, conversation_text: str) -> str:
        """Gerar resumo da conversa"""
        prompt = f"""
Analise esta conversa do WhatsApp e gere um resumo conciso em português brasileiro.

Conversa:
{conversation_text}

Instruções:
- Resuma os principais pontos da conversa
- Identifique o assunto principal
- Destaque informações importantes
- Máximo 200 palavras
- Seja objetivo e claro

Resumo:
"""
        
        try:
            response = self._call_ollama(prompt)
            return response.strip()
        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo: {e}")
            return "Erro ao gerar resumo"
    
    def _generate_summary_with_prompt(self, conversation_text: str) -> Dict:
        """Gerar resumo da conversa com prompt"""
        prompt = f"""
Analise esta conversa do WhatsApp e gere um resumo conciso em português brasileiro.

Conversa:
{conversation_text}

Instruções:
- Resuma os principais pontos da conversa
- Identifique o assunto principal
- Destaque informações importantes
- Máximo 200 palavras
- Seja objetivo e claro

Resumo:
"""
        
        try:
            response = self._call_ollama(prompt)
            return {
                "result": response.strip(),
                "prompt": prompt,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo: {e}")
            return {
                "result": "Erro ao gerar resumo",
                "prompt": prompt,
                "success": False,
                "error": str(e)
            }
    
    def _extract_topics(self, conversation_text: str) -> List[str]:
        """Extrair tópicos principais"""
        prompt = f"""
Analise esta conversa do WhatsApp e identifique os principais tópicos discutidos.

Conversa:
{conversation_text}

Instruções:
- Identifique 3-5 tópicos principais
- Use palavras-chave ou frases curtas
- Responda em formato de lista JSON
- Exemplo: ["trabalho", "família", "finanças", "saúde"]

Tópicos (formato JSON):
"""
        
        try:
            response = self._call_ollama(prompt)
            try:
                topics = json.loads(response.strip())
                return topics if isinstance(topics, list) else [response.strip()]
            except json.JSONDecodeError:
                topics = [line.strip() for line in response.strip().split('\n') if line.strip()]
                return topics[:5]
        except Exception as e:
            self.logger.error(f"Erro ao extrair tópicos: {e}")
            return ["Erro ao extrair tópicos"]
    
    def _extract_topics_with_prompt(self, conversation_text: str) -> Dict:
        """Extrair tópicos principais com prompt"""
        prompt = f"""
Analise esta conversa do WhatsApp e identifique os principais tópicos discutidos.

Conversa:
{conversation_text}

Instruções:
- Identifique 3-5 tópicos principais
- Use palavras-chave ou frases curtas
- Responda em formato de lista JSON
- Exemplo: ["trabalho", "família", "finanças", "saúde"]

Tópicos (formato JSON):
"""
        
        try:
            response = self._call_ollama(prompt)
            try:
                topics = json.loads(response.strip())
                result = topics if isinstance(topics, list) else [response.strip()]
            except json.JSONDecodeError:
                topics = [line.strip() for line in response.strip().split('\n') if line.strip()]
                result = topics[:5]
            
            return {
                "result": result,
                "prompt": prompt,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erro ao extrair tópicos: {e}")
            return {
                "result": ["Erro ao extrair tópicos"],
                "prompt": prompt,
                "success": False,
                "error": str(e)
            }
    
    def _analyze_sentiment(self, conversation_text: str) -> Dict[str, Any]:
        """Analisar sentimento da conversa"""
        prompt = f"""
Analise o sentimento geral desta conversa do WhatsApp.

Conversa:
{conversation_text}

Instruções:
- Analise o tom geral da conversa
- Identifique emoções predominantes
- Responda em formato JSON com:
  - "overall_sentiment": "positivo", "negativo" ou "neutro"
  - "confidence": valor de 0 a 1
  - "emotions": lista de emoções detectadas
  - "description": breve descrição do sentimento

Resposta (formato JSON):
"""
        
        try:
            response = self._call_ollama(prompt)
            try:
                sentiment_data = json.loads(response.strip())
                return sentiment_data
            except json.JSONDecodeError:
                return {
                    "overall_sentiment": "neutro",
                    "confidence": 0.5,
                    "emotions": ["neutro"],
                    "description": response.strip()
                }
        except Exception as e:
            self.logger.error(f"Erro ao analisar sentimento: {e}")
            return {
                "overall_sentiment": "neutro",
                "confidence": 0.0,
                "emotions": ["erro"],
                "description": "Erro na análise"
            }
    
    def _analyze_sentiment_with_prompt(self, conversation_text: str) -> Dict:
        """Analisar sentimento da conversa com prompt"""
        prompt = f"""
Analise o sentimento geral desta conversa do WhatsApp.

Conversa:
{conversation_text}

Instruções:
- Analise o tom geral da conversa
- Identifique emoções predominantes
- Responda em formato JSON com:
  - "overall_sentiment": "positivo", "negativo" ou "neutro"
  - "confidence": valor de 0 a 1
  - "emotions": lista de emoções detectadas
  - "description": breve descrição do sentimento

Resposta (formato JSON):
"""
        
        try:
            response = self._call_ollama(prompt)
            try:
                sentiment_data = json.loads(response.strip())
                result = sentiment_data
            except json.JSONDecodeError:
                result = {
                    "overall_sentiment": "neutro",
                    "confidence": 0.5,
                    "emotions": ["neutro"],
                    "description": response.strip()
                }
            
            return {
                "result": result,
                "prompt": prompt,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erro ao analisar sentimento: {e}")
            return {
                "result": {
                    "overall_sentiment": "neutro",
                    "confidence": 0.0,
                    "emotions": ["erro"],
                    "description": "Erro na análise"
                },
                "prompt": prompt,
                "success": False,
                "error": str(e)
            }
    
    def _generate_insights(self, conversation_text: str) -> List[str]:
        """Gerar insights sobre a conversa"""
        prompt = f"""
Analise esta conversa do WhatsApp e gere insights interessantes.

Conversa:
{conversation_text}

Instruções:
- Identifique padrões comportamentais
- Destaque informações importantes
- Gere 2-3 insights relevantes
- Seja específico e útil
- Responda em formato de lista

Insights:
"""
        
        try:
            response = self._call_ollama(prompt)
            insights = [line.strip() for line in response.strip().split('\n') if line.strip()]
            return insights[:3]
        except Exception as e:
            self.logger.error(f"Erro ao gerar insights: {e}")
            return ["Erro ao gerar insights"]
    
    def _generate_insights_with_prompt(self, conversation_text: str) -> Dict:
        """Gerar insights sobre a conversa com prompt"""
        prompt = f"""
Analise esta conversa do WhatsApp e gere insights interessantes.

Conversa:
{conversation_text}

Instruções:
- Identifique padrões comportamentais
- Destaque informações importantes
- Gere 2-3 insights relevantes
- Seja específico e útil
- Responda em formato de lista

Insights:
"""
        
        try:
            response = self._call_ollama(prompt)
            insights = [line.strip() for line in response.strip().split('\n') if line.strip()]
            result = insights[:3]
            
            return {
                "result": result,
                "prompt": prompt,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erro ao gerar insights: {e}")
            return {
                "result": ["Erro ao gerar insights"],
                "prompt": prompt,
                "success": False,
                "error": str(e)
            }
    
    def _calculate_stats(self, conversation_data: Dict) -> Dict[str, Any]:
        """Calcular estatísticas da conversa"""
        total_messages = 0
        audio_messages = 0
        text_messages = 0
        total_contacts = len(conversation_data.get('contacts', []))
        
        for contact in conversation_data.get('contacts', []):
            messages = contact.get('messages', [])
            total_messages += len(messages)
            
            for message in messages:
                if message.get('message_type') == 'audio':
                    audio_messages += 1
                else:
                    text_messages += 1
        
        return {
            'total_contacts': total_contacts,
            'total_messages': total_messages,
            'audio_messages': audio_messages,
            'text_messages': text_messages,
            'audio_percentage': (audio_messages / total_messages * 100) if total_messages > 0 else 0
        }
    
    def _call_ollama(self, prompt: str, max_retries: int = 3) -> str:
        """Chamar API do Ollama"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 1000
            }
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get('response', '').strip()
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                self.logger.warning(f"Tentativa {attempt + 1} falhou, tentando novamente: {e}")
                time.sleep(2 ** attempt)
        
        return ""
    
    def test_connection(self) -> Dict[str, Any]:
        """Testar conexão com Ollama"""
        self._ensure_initialized()
        self.logger.info("Testando conexao com Ollama...")
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            model_available = self.model in model_names
            if not model_available and model_names:
                self.model = model_names[0]
                model_available = True
            
            self.logger.info(f"Ollama conectado - {len(models)} modelos disponiveis")
            
            return {
                'connected': True,
                'model_available': model_available,
                'models': model_names,
                'selected_model': self.model
            }
            
        except Exception as e:
            self.logger.error(f"Erro de conexao: {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def test_simple_prompt(self, text: str = "Diga 'Ola' em portugues") -> Dict[str, Any]:
        """Testar prompt simples"""
        self._ensure_initialized()
        self.logger.info(f"Testando prompt simples: {text}")
        
        try:
            start_time = time.time()
            
            payload = {
                "model": self.model,
                "prompt": text,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 200
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get('response', '').strip()
            response_time = time.time() - start_time
            
            self.logger.info(f"Resposta recebida em {response_time:.2f}s")
            
            return {
                'success': True,
                'response': response_text,
                'response_time': response_time,
                'model': self.model
            }
            
        except Exception as e:
            self.logger.error(f"Erro no prompt: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_analysis(self, sample_text: str) -> bool:
        """Testar análise com texto de exemplo"""
        self._ensure_initialized()
        self.logger.info("Testando analise de conversa")
        
        try:
            test_data = {
                'conversation_id': 'test',
                'contacts': [{
                    'contact_name': 'Teste',
                    'messages': [{
                        'text': sample_text,
                        'message_type': 'text',
                        'timestamp': '10:00'
                    }]
                }]
            }
            
            result = self.analyze_conversation(test_data)
            
            if 'error' not in result:
                self.logger.info("Teste de analise OK")
                return True
            else:
                self.logger.error(f"Erro no teste: {result['error']}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no teste: {e}")
            return False
    
    def run_full_test(self) -> Dict[str, Any]:
        """Executar teste completo"""
        self._ensure_initialized()
        self.logger.info("Iniciando teste completo do LlamaService")
        
        results = {}
        
        # Teste 1: Conexão
        connection_result = self.test_connection()
        results['connection'] = connection_result
        
        if not connection_result['connected']:
            self.logger.error("Teste interrompido - Ollama nao esta rodando")
            return results
        
        # Teste 2: Prompt simples
        simple_result = self.test_simple_prompt()
        results['simple_prompt'] = simple_result
        
        if not simple_result['success']:
            self.logger.error("Teste interrompido - Erro no prompt simples")
            return results
        
        # Teste 3: Análise de conversa
        analysis_result = self.test_analysis("Ola, como voce esta?")
        results['analysis'] = analysis_result
        
        self.logger.info("Teste completo finalizado")
        return results
