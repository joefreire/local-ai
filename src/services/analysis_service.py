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
        
        # Estatísticas de uso
        self.usage_stats = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_time": 0.0,
            "start_time": time.time()
        }
        
        # System prompt para análise comercial
        self.system_prompt = """Você é um especialista em análise comercial e atendimento ao cliente. Sua função é analisar conversas do WhatsApp Business para extrair insights valiosos sobre:

1. QUALIDADE DO ATENDIMENTO: Avaliar se o funcionário foi eficaz, cortês e profissional
2. SATISFAÇÃO DO CLIENTE: Identificar sinais de satisfação, insatisfação ou neutralidade
3. OPORTUNIDADES DE VENDA: Detectar chances de upsell, cross-sell ou conversão
4. PADRÕES DE COMPORTAMENTO: Identificar necessidades, objeções e preferências dos clientes
5. MELHORIAS: Sugerir ações para aprimorar vendas e relacionamento

DIRETRIZES:
- Seja objetivo e focado em insights acionáveis
- Considere o contexto comercial e profissional
- Identifique padrões e tendências
- Forneça feedback construtivo
- Use linguagem clara e direta
- Foque em dados que agregam valor ao negócio"""
    
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
        """Analisar conversa completa (DEPRECATED - usar analyze_diary)"""
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
    
    def analyze_diary(self, diary_data: Dict) -> Dict:
        """Analisar diário completo - contatos individuais + resumo global (NOVO FLUXO)"""
        self._log_operation("análise de diário", {
            "diary_id": str(diary_data.get('_id')),
            "user_name": diary_data.get('user_name'),
            "contacts_count": len(diary_data.get('contacts', []))
        })
        
        try:
            if not diary_data or not diary_data.get('contacts'):
                return {'error': 'Dados de diário inválidos'}
            
            # 1. Analisar cada contato individualmente
            contact_analyses = []
            for contact_idx, contact in enumerate(diary_data.get('contacts', [])):
                contact_analysis = self._analyze_contact(contact, diary_data, contact_idx)
                if contact_analysis:
                    contact_analyses.append(contact_analysis)
            
            if not contact_analyses:
                return {'error': 'Nenhuma análise de contato válida gerada'}
            
            # 2. Gerar resumo global do diário
            diary_summary = self._generate_diary_summary(contact_analyses, diary_data)
            
            # 3. Compilar resultado final
            result = {
                'contact_analyses': contact_analyses,
                'diary_summary': diary_summary,
                'analysis_stats': self._calculate_analysis_stats(contact_analyses, diary_data),
                'analyzed_at': datetime.now().isoformat()
            }
            
            self._log_success("análise de diário", {
                "diary_id": str(diary_data.get('_id')),
                "contacts_analyzed": len(contact_analyses),
                "analysis_success_rate": len([c for c in contact_analyses if c.get('success', False)]) / len(contact_analyses) * 100
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao analisar diário: {e}")
            self.logger.error(f"Tipo do erro: {type(e).__name__}")
            import traceback
            self.logger.error(f"Traceback completo: {traceback.format_exc()}")
            return {
                'error': str(e),
                'error_type': type(e).__name__,
                'success': False
            }
    
    def _prepare_conversation_text(self, conversation_data: Dict) -> str:
        """Preparar texto da conversa para análise com contexto histórico"""
        text_parts = []
        
        # Adicionar contexto histórico se disponível
        historical_context = conversation_data.get('historical_context', [])
        if historical_context:
            text_parts.append("=== CONTEXTO HISTÓRICO (Últimos 7 dias) ===")
            text_parts.append("Mensagens recentes do mesmo usuário para contexto:")
            
            for msg in historical_context[:10]:  # Limitar a 10 mensagens históricas
                timestamp = msg.get('timestamp', '')
                contact_name = msg.get('contact_name', 'Desconhecido')
                message_type = msg.get('message_type', 'text')
                text = msg.get('text', '')
                
                if text:
                    prefix = f"[{timestamp}] {contact_name}: " if timestamp else f"{contact_name}: "
                    
                    # Adicionar prefixo baseado no tipo
                    if message_type == 'audio_transcribed':
                        prefix += "[ÁUDIO HISTÓRICO] "
                    elif message_type == 'image_analyzed':
                        prefix += "[IMAGEM HISTÓRICA] "
                    elif message_type in ['audio', 'image']:
                        prefix += f"[{message_type.upper()} HISTÓRICO] "
                    
                    text_parts.append(f"{prefix}{text}")
            
            text_parts.append("\n=== CONVERSA ATUAL ===")
        
        # Adicionar conversa atual
        for contact in conversation_data.get('contacts', []):
            contact_name = contact.get('contact_name', 'Desconhecido')
            text_parts.append(f"\n=== Conversa com {contact_name} ===")
            
            for message in contact.get('messages', []):
                message_text = message.get('text', '')
                message_type = message.get('message_type', 'text')
                
                if message_text:
                    timestamp = message.get('timestamp', '')
                    prefix = f"[{timestamp}] {contact_name}: " if timestamp else f"{contact_name}: "
                    
                    # Adicionar prefixo baseado no tipo
                    if message_type == 'audio_transcribed':
                        prefix += "[ÁUDIO TRANSCRITO] "
                    elif message_type == 'image_analyzed':
                        prefix += "[IMAGEM ANALISADA] "
                    elif message_type in ['audio', 'image']:
                        prefix += f"[{message_type.upper()}] "
                    
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
- Seja objetivo e claro

Resumo:
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
            return response.strip()
        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo: {e}")
            return "Erro ao gerar resumo"
    
    def _generate_summary_with_prompt(self, conversation_text: str) -> Dict:
        """Gerar resumo da conversa com prompt"""
        prompt = f"""
Analise esta conversa do WhatsApp e gere um resumo conciso em português brasileiro.

IMPORTANTE: A conversa pode incluir:
- Contexto histórico dos últimos 7 dias (marcado como HISTÓRICO)
- Mensagens de áudio transcritas (marcadas como [ÁUDIO TRANSCRITO])
- Análises de imagens (marcadas como [IMAGEM ANALISADA])
- Mensagens de texto normais

Conversa:
{conversation_text}

Instruções:
- Considere o contexto histórico para entender melhor a conversa atual
- Use as transcrições de áudio e análises de imagem como conteúdo real
- Resuma os principais pontos da conversa atual
- Identifique o assunto principal
- Destaque informações importantes
- Seja objetivo e claro

Resumo:
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
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
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
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

IMPORTANTE: A conversa pode incluir:
- Contexto histórico dos últimos 7 dias (marcado como HISTÓRICO)
- Mensagens de áudio transcritas (marcadas como [ÁUDIO TRANSCRITO])
- Análises de imagens (marcadas como [IMAGEM ANALISADA])
- Mensagens de texto normais

Conversa:
{conversation_text}

INSTRUÇÕES CRÍTICAS:
- Identifique exatamente 3-5 tópicos principais da conversa atual
- Use palavras-chave ou frases curtas (máximo 3 palavras por tópico)
- Responda APENAS com uma lista JSON válida
- NÃO inclua texto explicativo, apenas o JSON
- NÃO use markdown, apenas JSON puro

FORMATO OBRIGATÓRIO:
["tópico1", "tópico2", "tópico3"]

EXEMPLOS VÁLIDOS:
["educação", "matrícula", "cursos"]
["trabalho", "família", "finanças"]
["saúde", "médico", "tratamento"]

Responda APENAS com o JSON:
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
            response_clean = response.strip()
            
            # Tentar parse JSON direto
            try:
                topics = json.loads(response_clean)
                if isinstance(topics, list):
                    result = topics
                else:
                    result = [str(topics)]
            except json.JSONDecodeError:
                # Tentar extrair JSON da resposta
                import re
                json_match = re.search(r'\[.*?\]', response_clean, re.DOTALL)
                if json_match:
                    try:
                        topics = json.loads(json_match.group())
                        result = topics if isinstance(topics, list) else [str(topics)]
                    except json.JSONDecodeError:
                        # Fallback: extrair tópicos das linhas
                        lines = [line.strip() for line in response_clean.split('\n') if line.strip()]
                        result = [line.replace('"', '').replace(',', '').strip() for line in lines if line and not line.startswith(('Aqui estão', '```', '['))]
                        result = [topic for topic in result if topic and len(topic) > 1][:5]
                else:
                    # Fallback final
                    result = ["tópicos não identificados"]
            
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
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
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

IMPORTANTE: A conversa pode incluir:
- Contexto histórico dos últimos 7 dias (marcado como HISTÓRICO)
- Mensagens de áudio transcritas (marcadas como [ÁUDIO TRANSCRITO])
- Análises de imagens (marcadas como [IMAGEM ANALISADA])
- Mensagens de texto normais

Conversa:
{conversation_text}

Instruções:
- Considere o contexto histórico para entender a evolução emocional
- Use as transcrições de áudio e análises de imagem como conteúdo real
- Analise o tom geral da conversa atual
- Identifique emoções predominantes
- Responda em formato JSON com:
  - "overall_sentiment": "positivo", "negativo" ou "neutro"
  - "confidence": valor de 0 a 1
  - "emotions": lista de emoções detectadas
  - "description": breve descrição do sentimento

Resposta (formato JSON):
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
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
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
            insights = [line.strip() for line in response.strip().split('\n') if line.strip()]
            return insights[:3]
        except Exception as e:
            self.logger.error(f"Erro ao gerar insights: {e}")
            return ["Erro ao gerar insights"]
    
    def _generate_insights_with_prompt(self, conversation_text: str) -> Dict:
        """Gerar insights sobre a conversa com prompt"""
        prompt = f"""
Analise esta conversa do WhatsApp e gere insights interessantes.

IMPORTANTE: A conversa pode incluir:
- Contexto histórico dos últimos 7 dias (marcado como HISTÓRICO)
- Mensagens de áudio transcritas (marcadas como [ÁUDIO TRANSCRITO])
- Análises de imagens (marcadas como [IMAGEM ANALISADA])
- Mensagens de texto normais

Conversa:
{conversation_text}

INSTRUÇÕES CRÍTICAS:
- Identifique padrões comportamentais recorrentes
- Destaque informações importantes da conversa atual
- Compare com o histórico para identificar mudanças
- Gere exatamente 3 insights relevantes e específicos
- Cada insight deve ser uma frase clara e acionável
- Responda APENAS com uma lista JSON válida
- NÃO inclua texto explicativo, apenas o JSON
- NÃO use markdown, apenas JSON puro

FORMATO OBRIGATÓRIO:
["insight 1", "insight 2", "insight 3"]

EXEMPLOS VÁLIDOS:
["Cliente demonstra interesse recorrente em cursos de tecnologia", "Padrão de dúvidas sobre preços sugere sensibilidade financeira", "Comunicação formal indica perfil corporativo"]

Responda APENAS com o JSON:
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
            response_clean = response.strip()
            
            # Tentar parse JSON direto
            try:
                insights = json.loads(response_clean)
                if isinstance(insights, list):
                    result = insights
                else:
                    result = [str(insights)]
            except json.JSONDecodeError:
                # Tentar extrair JSON da resposta
                import re
                json_match = re.search(r'\[.*?\]', response_clean, re.DOTALL)
                if json_match:
                    try:
                        insights = json.loads(json_match.group())
                        result = insights if isinstance(insights, list) else [str(insights)]
                    except json.JSONDecodeError:
                        # Fallback: extrair insights das linhas
                        lines = [line.strip() for line in response_clean.split('\n') if line.strip()]
                        result = []
                        for line in lines:
                            line_clean = line.replace('"', '').replace(',', '').replace('**', '').replace('*', '').strip()
                            if line_clean and not line_clean.startswith(('Aqui estão', '```', '[', 'Insight')):
                                result.append(line_clean)
                        result = result[:3]
                else:
                    # Fallback final
                    result = ["insights não identificados"]
            
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
    
    def _call_ollama(self, prompt: str, max_retries: int = 3, system_prompt: str = None) -> str:
        """Chamar API do Ollama com estatísticas detalhadas"""
        start_time = time.time()
        
        # Calcular estatísticas do prompt
        prompt_tokens = len(prompt.split())  # Aproximação simples
        system_tokens = len(system_prompt.split()) if system_prompt else 0
        total_input_tokens = prompt_tokens + system_tokens
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "top_p": 0.9,
                "repeat_penalty": 1.15,
                "num_predict": 1536
            }
        }
        
        # Adicionar system prompt se fornecido
        if system_prompt:
            payload["system"] = system_prompt
        
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"🔄 Chamada Ollama - Tentativa {attempt + 1}")
                self.logger.debug(f"📊 Input: {total_input_tokens} tokens (prompt: {prompt_tokens}, system: {system_tokens})")
                
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Calcular estatísticas da resposta
                end_time = time.time()
                duration = end_time - start_time
                output_tokens = len(response_text.split())  # Aproximação simples
                tokens_per_second = output_tokens / duration if duration > 0 else 0
                
                # Atualizar estatísticas globais
                self.usage_stats["total_requests"] += 1
                self.usage_stats["total_input_tokens"] += total_input_tokens
                self.usage_stats["total_output_tokens"] += output_tokens
                self.usage_stats["total_time"] += duration
                
                # Log detalhado das estatísticas
                self.logger.info(f"✅ Ollama Response - {duration:.2f}s")
                self.logger.info(f"📊 Tokens: {total_input_tokens} → {output_tokens} (total: {total_input_tokens + output_tokens})")
                self.logger.info(f"⚡ Velocidade: {tokens_per_second:.2f} tokens/s")
                self.logger.info(f"🎯 Modelo: {self.model}")
                
                # Log de estatísticas acumuladas
                total_tokens = self.usage_stats["total_input_tokens"] + self.usage_stats["total_output_tokens"]
                avg_speed = total_tokens / self.usage_stats["total_time"] if self.usage_stats["total_time"] > 0 else 0
                self.logger.info(f"📈 ACUMULADO: {self.usage_stats['total_requests']} requests, {total_tokens} tokens, {avg_speed:.2f} tokens/s médio")
                
                # Log de performance
                if duration > 30:
                    self.logger.warning(f"⚠️  Resposta lenta: {duration:.2f}s")
                elif duration < 5:
                    self.logger.info(f"🚀 Resposta rápida: {duration:.2f}s")
                
                return response_text
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"❌ Falha final após {max_retries} tentativas: {e}")
                    raise e
                self.logger.warning(f"⚠️  Tentativa {attempt + 1} falhou, tentando novamente: {e}")
                time.sleep(2 ** attempt)
        
        return ""
    
    def get_usage_stats(self) -> Dict:
        """Obter estatísticas de uso do Ollama"""
        # Garantir que usage_stats existe
        if not hasattr(self, 'usage_stats'):
            self.usage_stats = {
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_time": 0.0,
                "start_time": time.time()
            }
        
        uptime = time.time() - self.usage_stats["start_time"]
        total_tokens = self.usage_stats["total_input_tokens"] + self.usage_stats["total_output_tokens"]
        
        return {
            "model": self.model,
            "total_requests": self.usage_stats["total_requests"],
            "total_input_tokens": self.usage_stats["total_input_tokens"],
            "total_output_tokens": self.usage_stats["total_output_tokens"],
            "total_tokens": total_tokens,
            "total_time": self.usage_stats["total_time"],
            "uptime": uptime,
            "avg_tokens_per_second": total_tokens / self.usage_stats["total_time"] if self.usage_stats["total_time"] > 0 else 0,
            "requests_per_minute": self.usage_stats["total_requests"] / (uptime / 60) if uptime > 0 else 0,
            "avg_response_time": self.usage_stats["total_time"] / self.usage_stats["total_requests"] if self.usage_stats["total_requests"] > 0 else 0
        }
    
    def print_usage_stats(self):
        """Imprimir estatísticas de uso"""
        stats = self.get_usage_stats()
        
        print("\n" + "=" * 60)
        print("📊 ESTATÍSTICAS DE USO DO OLLAMA")
        print("=" * 60)
        print(f"🤖 Modelo: {stats['model']}")
        print(f"📈 Requests: {stats['total_requests']}")
        print(f"📥 Input Tokens: {stats['total_input_tokens']:,}")
        print(f"📤 Output Tokens: {stats['total_output_tokens']:,}")
        print(f"🎯 Total Tokens: {stats['total_tokens']:,}")
        print(f"⏱️  Tempo Total: {stats['total_time']:.2f}s")
        print(f"🚀 Velocidade Média: {stats['avg_tokens_per_second']:.2f} tokens/s")
        print(f"📊 Requests/min: {stats['requests_per_minute']:.2f}")
        print(f"⚡ Tempo Médio/Request: {stats['avg_response_time']:.2f}s")
        print(f"🕐 Uptime: {stats['uptime']:.2f}s")
        print("=" * 60)
    
    def _analyze_contact(self, contact: Dict, diary_data: Dict, contact_idx: int) -> Optional[Dict]:
        """Analisar conversa individual de um contato"""
        try:
            contact_name = contact.get('contact_name', 'Desconhecido')
            messages = contact.get('messages', [])
            
            if not messages:
                return None
            
            # Preparar texto da conversa do contato
            conversation_text = self._prepare_contact_conversation_text(contact, diary_data)
            
            if not conversation_text.strip():
                return None
            
            # Análise completa do contato
            analysis = {
                'contact_name': contact_name,
                'contact_phone': contact.get('contact_phone', ''),
                'contact_key': contact.get('contact_key', ''),
                'contact_idx': contact_idx,
                'summary': self._generate_contact_summary(conversation_text, contact_name, diary_data),
                'topics': self._extract_contact_topics(conversation_text, contact_name, diary_data),
                'sentiment': self._analyze_contact_sentiment(conversation_text, contact_name, diary_data),
                'insights': self._generate_contact_insights(conversation_text, contact_name, diary_data),
                'conversation_stats': self._calculate_contact_stats(contact),
                'success': True,
                'analyzed_at': datetime.now().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Erro ao analisar contato {contact.get('contact_name', 'Desconhecido')}: {e}")
            return {
                'contact_name': contact.get('contact_name', 'Desconhecido'),
                'contact_idx': contact_idx,
                'error': str(e),
                'success': False,
                'analyzed_at': datetime.now().isoformat()
            }
    
    def _prepare_contact_conversation_text(self, contact: Dict, diary_data: Dict) -> str:
        """Preparar texto da conversa de um contato específico"""
        text_parts = []
        contact_name = contact.get('contact_name', 'Desconhecido')
        
        # Adicionar contexto histórico se disponível
        historical_context = diary_data.get('historical_context', [])
        if historical_context:
            # Filtrar apenas mensagens deste contato
            contact_historical = [
                msg for msg in historical_context 
                if msg.get('contact_name') == contact_name or msg.get('contact_key') == contact.get('contact_key')
            ]
            
            if contact_historical:
                text_parts.append("=== CONTEXTO HISTÓRICO (Últimos 7 dias) ===")
                text_parts.append(f"Mensagens recentes com {contact_name}:")
                
                for msg in contact_historical[:5]:  # Limitar a 5 mensagens históricas
                    timestamp = msg.get('timestamp', '')
                    message_type = msg.get('message_type', 'text')
                    text = msg.get('text', '')
                    
                    if text:
                        prefix = f"[{timestamp}] " if timestamp else ""
                        
                        # Adicionar prefixo baseado no tipo
                        if message_type == 'audio_transcribed':
                            prefix += "[ÁUDIO HISTÓRICO] "
                        elif message_type == 'image_analyzed':
                            prefix += "[IMAGEM HISTÓRICA] "
                        elif message_type in ['audio', 'image']:
                            prefix += f"[{message_type.upper()} HISTÓRICO] "
                        
                        text_parts.append(f"{prefix}{text}")
                
                text_parts.append("\n=== CONVERSA ATUAL ===")
        
        # Adicionar conversa atual do contato
        text_parts.append(f"\n=== Conversa com {contact_name} ===")
        
        for message in contact.get('messages', []):
            message_text = message.get('text', '')
            message_type = message.get('message_type', 'text')
            
            if message_text:
                timestamp = message.get('timestamp', '')
                from_me = message.get('from_me', False)
                sender = "Você" if from_me else contact_name
                prefix = f"[{timestamp}] {sender}: " if timestamp else f"{sender}: "
                
                # Adicionar prefixo baseado no tipo
                if message_type == 'audio_transcribed':
                    prefix += "[ÁUDIO TRANSCRITO] "
                elif message_type == 'image_analyzed':
                    prefix += "[IMAGEM ANALISADA] "
                elif message_type in ['audio', 'image']:
                    prefix += f"[{message_type.upper()}] "
                
                text_parts.append(f"{prefix}{message_text}")
        
        return "\n".join(text_parts)
    
    def _generate_contact_summary(self, conversation_text: str, contact_name: str, diary_data: Dict) -> Dict:
        """Gerar resumo da conversa com um contato específico"""
        user_name = diary_data.get('user_name', 'Usuário')
        company_name = diary_data.get('company_name', 'Empresa')
        date_formatted = diary_data.get('date_formatted', 'Data')
        
        prompt = f"""
CONTEXTO DA ANÁLISE:
Você está analisando uma conversa do WhatsApp Business de um dia de trabalho específico.

DADOS DO USUÁRIO:
- Nome: {user_name}
- Empresa: {company_name}
- Data: {date_formatted}
- Papel: Funcionário/Atendente da empresa

DADOS DO CONTATO:
- Nome: {contact_name}
- Papel: Cliente/Lead/Prospect da empresa
- Relacionamento: Conversa comercial/profissional

PROPÓSITO DA ANÁLISE:
Esta análise faz parte de um sistema de inteligência empresarial que:
1. Avalia a qualidade do atendimento ao cliente
2. Identifica oportunidades de melhoria no relacionamento
3. Extrai insights sobre necessidades dos clientes
4. Monitora padrões de comunicação e vendas
5. Gera feedback para treinamento e desenvolvimento

CONVERSA A SER ANALISADA:
{conversation_text}

INSTRUÇÕES ESPECÍFICAS:
- Analise a conversa do ponto de vista de atendimento ao cliente
- Identifique o nível de satisfação do cliente {contact_name}
- Avalie a efetividade da comunicação de {user_name}
- Destaque oportunidades de venda ou upsell
- Identifique problemas ou objeções do cliente
- Avalie se o atendimento foi resolutivo
- Considere o contexto histórico para entender a evolução do relacionamento
- Use transcrições de áudio e análises de imagem como conteúdo real
- Seja objetivo e focado em insights acionáveis

Resumo da conversa com {contact_name}:
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
            return {
                "result": response.strip(),
                "prompt": prompt,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo do contato: {e}")
            return {
                "result": f"Erro ao gerar resumo da conversa com {contact_name}",
                "prompt": prompt,
                "success": False,
                "error": str(e)
            }
    
    def _extract_contact_topics(self, conversation_text: str, contact_name: str, diary_data: Dict) -> Dict:
        """Extrair tópicos da conversa com um contato específico"""
        user_name = diary_data.get('user_name', 'Usuário')
        company_name = diary_data.get('company_name', 'Empresa')
        
        prompt = f"""
CONTEXTO:
Você está analisando uma conversa comercial do WhatsApp Business entre:
- {user_name} (funcionário da {company_name})
- {contact_name} (cliente/lead)

PROPÓSITO:
Identificar os principais tópicos de negócio discutidos para categorização e análise de vendas.

CONVERSA:
{conversation_text}

INSTRUÇÕES:
- Identifique 3-5 tópicos principais relacionados a NEGÓCIOS/VENDAS/ATENDIMENTO
- Foque em: produtos, serviços, preços, dúvidas, objeções, necessidades, problemas
- Use palavras-chave comerciais (máximo 3 palavras por tópico)
- Responda APENAS com JSON válido
- NÃO inclua texto explicativo

EXEMPLOS DE TÓPICOS COMERCIAIS:
["produto", "preço", "desconto"]
["dúvida", "especificação", "prazo"]
["objeção", "concorrência", "custo"]
["necessidade", "solução", "benefício"]

Responda APENAS com o JSON:
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
            response_clean = response.strip()
            
            # Tentar parse JSON direto
            try:
                topics = json.loads(response_clean)
                if isinstance(topics, list):
                    result = topics
                else:
                    result = [str(topics)]
            except json.JSONDecodeError:
                # Tentar extrair JSON da resposta
                import re
                json_match = re.search(r'\[.*?\]', response_clean, re.DOTALL)
                if json_match:
                    try:
                        topics = json.loads(json_match.group())
                        result = topics if isinstance(topics, list) else [str(topics)]
                    except json.JSONDecodeError:
                        # Fallback: extrair tópicos das linhas
                        lines = [line.strip() for line in response_clean.split('\n') if line.strip()]
                        result = [line.replace('"', '').replace(',', '').strip() for line in lines if line and not line.startswith(('Aqui estão', '```', '['))]
                        result = [topic for topic in result if topic and len(topic) > 1][:5]
                else:
                    # Fallback final
                    result = ["tópicos não identificados"]
            
            return {
                "result": result,
                "prompt": prompt,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erro ao extrair tópicos do contato: {e}")
            return {
                "result": ["Erro ao extrair tópicos"],
                "prompt": prompt,
                "success": False,
                "error": str(e)
            }
    
    def _analyze_contact_sentiment(self, conversation_text: str, contact_name: str, diary_data: Dict) -> Dict:
        """Analisar sentimento da conversa com um contato específico"""
        user_name = diary_data.get('user_name', 'Usuário')
        company_name = diary_data.get('company_name', 'Empresa')
        
        prompt = f"""
CONTEXTO COMERCIAL:
Você está analisando o sentimento de uma conversa de vendas/atendimento entre:
- {user_name} (funcionário da {company_name})
- {contact_name} (cliente/lead)

PROPÓSITO:
Avaliar a satisfação do cliente e a efetividade do atendimento para melhorar o relacionamento comercial.

CONVERSA:
{conversation_text}

INSTRUÇÕES:
- Analise o sentimento do CLIENTE ({contact_name}) em relação ao atendimento
- Avalie a efetividade da comunicação do FUNCIONÁRIO ({user_name})
- Identifique sinais de satisfação, insatisfação, interesse ou desinteresse
- Considere o contexto histórico para entender a evolução do relacionamento
- Use transcrições de áudio e análises de imagem como conteúdo real
- Foque em aspectos comerciais: interesse em comprar, confiança, objeções

Responda em formato JSON:
{{
  "overall_sentiment": "positivo/negativo/neutro",
  "confidence": 0.0-1.0,
  "emotions": ["interesse", "satisfação", "dúvida", "frustração", etc],
  "description": "Breve análise do sentimento comercial"
}}

Resposta (formato JSON):
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
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
            self.logger.error(f"Erro ao analisar sentimento do contato: {e}")
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
    
    def _generate_contact_insights(self, conversation_text: str, contact_name: str, diary_data: Dict) -> Dict:
        """Gerar insights sobre a conversa com um contato específico"""
        user_name = diary_data.get('user_name', 'Usuário')
        company_name = diary_data.get('company_name', 'Empresa')
        
        prompt = f"""
CONTEXTO COMERCIAL:
Você está analisando uma conversa de vendas/atendimento entre:
- {user_name} (funcionário da {company_name})
- {contact_name} (cliente/lead)

PROPÓSITO:
Gerar insights acionáveis para melhorar vendas, atendimento e relacionamento com o cliente.

CONVERSA:
{conversation_text}

INSTRUÇÕES:
- Gere 3 insights COMERCIAIS específicos sobre {contact_name}
- Foque em: perfil do cliente, necessidades, objeções, oportunidades de venda
- Identifique padrões de comportamento e preferências
- Destaque sinais de interesse ou desinteresse
- Compare com histórico para identificar evolução
- Cada insight deve ser acionável para vendas/atendimento
- Responda APENAS com JSON válido

EXEMPLOS DE INSIGHTS COMERCIAIS:
["Cliente demonstra alto interesse em produtos premium", "Sensibilidade a preços sugere foco em soluções econômicas", "Comunicação formal indica perfil B2B corporativo"]
["Lead apresenta objeções sobre prazo de entrega", "Necessidade específica de customização identificada", "Sinal de interesse em proposta comercial"]

Responda APENAS com o JSON:
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
            response_clean = response.strip()
            
            # Tentar parse JSON direto
            try:
                insights = json.loads(response_clean)
                if isinstance(insights, list):
                    result = insights
                else:
                    result = [str(insights)]
            except json.JSONDecodeError:
                # Tentar extrair JSON da resposta
                import re
                json_match = re.search(r'\[.*?\]', response_clean, re.DOTALL)
                if json_match:
                    try:
                        insights = json.loads(json_match.group())
                        result = insights if isinstance(insights, list) else [str(insights)]
                    except json.JSONDecodeError:
                        # Fallback: extrair insights das linhas
                        lines = [line.strip() for line in response_clean.split('\n') if line.strip()]
                        result = []
                        for line in lines:
                            line_clean = line.replace('"', '').replace(',', '').replace('**', '').replace('*', '').strip()
                            if line_clean and not line_clean.startswith(('Aqui estão', '```', '[', 'Insight')):
                                result.append(line_clean)
                        result = result[:3]
                else:
                    # Fallback final
                    result = ["insights não identificados"]
            
            return {
                "result": result,
                "prompt": prompt,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erro ao gerar insights do contato: {e}")
            return {
                "result": ["Erro ao gerar insights"],
                "prompt": prompt,
                "success": False,
                "error": str(e)
            }
    
    def _calculate_contact_stats(self, contact: Dict) -> Dict[str, Any]:
        """Calcular estatísticas da conversa com um contato"""
        messages = contact.get('messages', [])
        total_messages = len(messages)
        audio_messages = 0
        text_messages = 0
        image_messages = 0
        sent_messages = 0
        received_messages = 0
        
        for message in messages:
            message_type = message.get('message_type', 'text')
            from_me = message.get('from_me', False)
            
            if from_me:
                sent_messages += 1
            else:
                received_messages += 1
            
            if message_type == 'audio':
                audio_messages += 1
            elif message_type == 'image':
                image_messages += 1
            else:
                text_messages += 1
        
        return {
            'total_messages': total_messages,
            'sent_messages': sent_messages,
            'received_messages': received_messages,
            'audio_messages': audio_messages,
            'text_messages': text_messages,
            'image_messages': image_messages,
            'audio_percentage': (audio_messages / total_messages * 100) if total_messages > 0 else 0,
            'text_percentage': (text_messages / total_messages * 100) if total_messages > 0 else 0,
            'image_percentage': (image_messages / total_messages * 100) if total_messages > 0 else 0
        }
    
    def _generate_diary_summary(self, contact_analyses: List[Dict], diary_data: Dict) -> Dict:
        """Gerar resumo global do diário baseado nas análises dos contatos"""
        # Preparar dados consolidados
        successful_analyses = [ca for ca in contact_analyses if ca.get('success', False)]
        
        if not successful_analyses:
            return {
                "result": "Nenhuma análise de contato válida disponível",
                "success": False
            }
        
        # Consolidar informações
        all_topics = []
        all_sentiments = []
        all_insights = []
        contact_summaries = []
        
        for analysis in successful_analyses:
            contact_name = analysis.get('contact_name', 'Desconhecido')
            
            # Tópicos
            topics = analysis.get('topics', {}).get('result', [])
            if isinstance(topics, list):
                # Garantir que cada item é uma string, não uma lista
                for topic in topics:
                    if isinstance(topic, str):
                        all_topics.append(topic)
                    elif isinstance(topic, list):
                        all_topics.extend([str(t) for t in topic if isinstance(t, str)])
            
            # Sentimentos
            sentiment = analysis.get('sentiment', {}).get('result', {})
            if isinstance(sentiment, dict):
                all_sentiments.append(sentiment)
            
            # Insights
            insights = analysis.get('insights', {}).get('result', [])
            if isinstance(insights, list):
                # Garantir que cada item é uma string, não uma lista
                for insight in insights:
                    if isinstance(insight, str):
                        all_insights.append(insight)
                    elif isinstance(insight, list):
                        all_insights.extend([str(i) for i in insight if isinstance(i, str)])
            
            # Resumos
            summary = analysis.get('summary', {}).get('result', '')
            if summary:
                contact_summaries.append(f"{contact_name}: {summary}")
        
        # Gerar prompt para resumo global
        consolidated_text = f"""
RESUMOS DAS CONVERSAS:
{chr(10).join(contact_summaries)}

TÓPICOS IDENTIFICADOS: {', '.join(set(all_topics))}

SENTIMENTOS: {len(all_sentiments)} conversas analisadas

INSIGHTS: {chr(10).join(set(all_insights))}
"""
        
        prompt = f"""
CONTEXTO EMPRESARIAL:
Você está analisando o desempenho comercial de um dia de trabalho específico.

DADOS DO FUNCIONÁRIO:
- Nome: {diary_data.get('user_name', 'Desconhecido')}
- Empresa: {diary_data.get('company_name', 'Desconhecida')}
- Data: {diary_data.get('date_formatted', 'Data não disponível')}
- Total de clientes atendidos: {len(contact_analyses)}

PROPÓSITO DA ANÁLISE:
Gerar um relatório executivo estruturado para:
1. Avaliar performance comercial do funcionário
2. Identificar oportunidades de melhoria
3. Destacar pontos fortes e fracos
4. Fornecer feedback acionável para desenvolvimento
5. Analisar padrões de vendas e atendimento

DADOS CONSOLIDADOS DO DIA:
{consolidated_text}

INSTRUÇÕES ESPECÍFICAS:
- Analise o desempenho COMERCIAL do funcionário
- Avalie qualidade do atendimento aos clientes
- Identifique padrões de vendas e conversão
- Destaque oportunidades de upsell/cross-sell perdidas
- Avalie efetividade da comunicação
- Identifique necessidades de treinamento
- Forneça feedback construtivo e acionável
- Foque em insights comerciais práticos

FORMATO DE RESPOSTA OBRIGATÓRIO (JSON):
{{
  "executive_summary": "Resumo executivo geral do desempenho do dia",
  "key_insights": [
    "Insight 1 sobre padrões comerciais identificados",
    "Insight 2 sobre comportamento do funcionário",
    "Insight 3 sobre oportunidades de negócio"
  ],
  "improvements": [
    "Melhoria 1 específica e acionável",
    "Melhoria 2 com foco em vendas/atendimento",
    "Melhoria 3 para desenvolvimento profissional"
  ],
  "feedback": {{
    "strengths": ["Ponto forte 1", "Ponto forte 2"],
    "weaknesses": ["Ponto de melhoria 1", "Ponto de melhoria 2"],
    "recommendations": ["Recomendação 1", "Recomendação 2"]
  }},
  "commercial_metrics": {{
    "customer_satisfaction": "alta/média/baixa",
    "sales_effectiveness": "alta/média/baixa",
    "communication_quality": "alta/média/baixa"
  }},
  "next_actions": [
    "Ação imediata 1 para implementar",
    "Ação de médio prazo 2",
    "Ação de longo prazo 3"
  ]
}}

Responda APENAS com o JSON válido:
"""
        
        try:
            response = self._call_ollama(prompt, system_prompt=self.system_prompt)
            
            # Tentar extrair JSON estruturado
            try:
                structured_data = json.loads(response.strip())
                
                # Validar campos obrigatórios
                required_fields = ['executive_summary', 'key_insights', 'improvements', 'feedback']
                if all(field in structured_data for field in required_fields):
                    return {
                        "result": structured_data.get('executive_summary', ''),
                        "key_insights": structured_data.get('key_insights', []),
                        "improvements": structured_data.get('improvements', []),
                        "feedback": structured_data.get('feedback', {}),
                        "commercial_metrics": structured_data.get('commercial_metrics', {}),
                        "next_actions": structured_data.get('next_actions', []),
                        "prompt": prompt,
                        "success": True,
                        "consolidated_data": {
                            "total_contacts": len(contact_analyses),
                            "successful_analyses": len(successful_analyses),
                            "unique_topics": list(set(all_topics)),
                            "sentiment_summary": self._calculate_sentiment_summary(all_sentiments),
                            "raw_insights": list(set(all_insights))[:5]
                        }
                    }
                else:
                    # Fallback se JSON estiver incompleto
                    return {
                        "result": response.strip(),
                        "key_insights": [],
                        "improvements": [],
                        "feedback": {},
                        "commercial_metrics": {},
                        "next_actions": [],
                        "prompt": prompt,
                        "success": True,
                        "consolidated_data": {
                            "total_contacts": len(contact_analyses),
                            "successful_analyses": len(successful_analyses),
                            "unique_topics": list(set(all_topics)),
                            "sentiment_summary": self._calculate_sentiment_summary(all_sentiments),
                            "raw_insights": list(set(all_insights))[:5]
                        }
                    }
            except json.JSONDecodeError:
                # Fallback se não conseguir fazer parse do JSON
                return {
                    "result": response.strip(),
                    "key_insights": [],
                    "improvements": [],
                    "feedback": {},
                    "commercial_metrics": {},
                    "next_actions": [],
                    "prompt": prompt,
                    "success": True,
                    "consolidated_data": {
                        "total_contacts": len(contact_analyses),
                        "successful_analyses": len(successful_analyses),
                        "unique_topics": list(set(all_topics)),
                        "sentiment_summary": self._calculate_sentiment_summary(all_sentiments),
                        "raw_insights": list(set(all_insights))[:5]
                    }
                }
        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo global: {e}")
            return {
                "result": "Erro ao gerar resumo global do diário",
                "key_insights": [],
                "improvements": [],
                "feedback": {},
                "commercial_metrics": {},
                "next_actions": [],
                "prompt": prompt,
                "success": False,
                "error": str(e)
            }
    
    def _calculate_sentiment_summary(self, sentiments: List[Dict]) -> Dict:
        """Calcular resumo dos sentimentos"""
        if not sentiments:
            return {"overall": "neutro", "confidence": 0.0}
        
        positive_count = sum(1 for s in sentiments if s.get('overall_sentiment') == 'positivo')
        negative_count = sum(1 for s in sentiments if s.get('overall_sentiment') == 'negativo')
        neutral_count = sum(1 for s in sentiments if s.get('overall_sentiment') == 'neutro')
        
        total = len(sentiments)
        
        if positive_count > negative_count and positive_count > neutral_count:
            overall = "positivo"
        elif negative_count > positive_count and negative_count > neutral_count:
            overall = "negativo"
        else:
            overall = "neutro"
        
        avg_confidence = sum(s.get('confidence', 0) for s in sentiments) / total
        
        return {
            "overall": overall,
            "confidence": avg_confidence,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_conversations": total
        }
    
    def _calculate_analysis_stats(self, contact_analyses: List[Dict], diary_data: Dict) -> Dict[str, Any]:
        """Calcular estatísticas gerais da análise"""
        successful_analyses = [ca for ca in contact_analyses if ca.get('success', False)]
        
        total_messages = sum(ca.get('conversation_stats', {}).get('total_messages', 0) for ca in successful_analyses)
        total_audio = sum(ca.get('conversation_stats', {}).get('audio_messages', 0) for ca in successful_analyses)
        total_text = sum(ca.get('conversation_stats', {}).get('text_messages', 0) for ca in successful_analyses)
        total_images = sum(ca.get('conversation_stats', {}).get('image_messages', 0) for ca in successful_analyses)
        
        return {
            'total_contacts': len(contact_analyses),
            'successful_analyses': len(successful_analyses),
            'failed_analyses': len(contact_analyses) - len(successful_analyses),
            'success_rate': (len(successful_analyses) / len(contact_analyses) * 100) if contact_analyses else 0,
            'total_messages_analyzed': total_messages,
            'total_audio_messages': total_audio,
            'total_text_messages': total_text,
            'total_image_messages': total_images,
            'user_name': diary_data.get('user_name', 'Desconhecido'),
            'company_name': diary_data.get('company_name', 'Desconhecida'),
            'diary_date': diary_data.get('date_formatted', 'Data não disponível')
        }
    
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
                    "temperature": 0.4,
                    "top_p": 0.9,
                    "repeat_penalty": 1.15,
                    "num_predict": 1536
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
