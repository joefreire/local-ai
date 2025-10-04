"""
Service para análise de conversas por contatos/atendentes
"""
from datetime import datetime
from typing import List, Dict, Optional, Any
import json

from .base_service import BaseService
from .analysis_service import LlamaService
from .database_service import DatabaseService
from ..config import Config

class ContactAnalysisService(BaseService):
    """Service para análise detalhada de conversas por contatos"""
    
    def _initialize(self):
        """Inicializar services"""
        self.llama_service = LlamaService()
        self.db_service = DatabaseService()
        self._ensure_llama_service_initialized()
    
    def _ensure_llama_service_initialized(self):
        """Garantir que o LlamaService está inicializado"""
        if hasattr(self, 'llama_service'):
            self.llama_service._ensure_initialized()
        else:
            self.logger.error("LlamaService não foi inicializado")
    
    def analyze_conversation_by_contacts(self, conversation_id: str) -> Dict[str, Any]:
        """Analisar conversa por contatos individuais"""
        self._ensure_initialized()
        self._log_operation("análise por contatos", {"conversation_id": conversation_id})
        
        try:
            # 1. Buscar dados da conversa
            conversation_data = self.db_service.get_conversation_text_for_analysis(conversation_id)
            if not conversation_data:
                return {'error': 'Conversa não encontrada'}
            
            # 2. Analisar cada contato individualmente
            contact_analyses = []
            for contact in conversation_data.get('contacts', []):
                contact_analysis = self._analyze_single_contact(contact, conversation_data)
                if contact_analysis:
                    contact_analyses.append(contact_analysis)
            
            # 3. Gerar análise geral da conversa
            overall_analysis = self._generate_overall_analysis(contact_analyses, conversation_data)
            
            # 4. Compilar resultado final
            result = {
                'conversation_id': conversation_id,
                'user_name': conversation_data.get('user_name'),
                'date': conversation_data.get('date'),
                'analysis_timestamp': datetime.now().isoformat(),
                'contacts_analyzed': len(contact_analyses),
                'contact_analyses': contact_analyses,
                'overall_analysis': overall_analysis,
                'summary': self._generate_executive_summary(contact_analyses, overall_analysis)
            }
            
            # 5. Salvar no banco
            self._save_contact_analysis(conversation_id, result)
            
            self._log_success("análise por contatos", {"contacts_analyzed": len(contact_analyses)})
            return result
            
        except Exception as e:
            self._log_error("análise por contatos", e)
            return {'error': str(e)}
    
    def _analyze_single_contact(self, contact: Dict, conversation_data: Dict) -> Optional[Dict]:
        """Analisar um contato específico"""
        try:
            contact_name = contact.get('contact_name', 'Desconhecido')
            messages = contact.get('messages', [])
            
            if not messages:
                return None
            
            # Preparar texto da conversa com este contato
            contact_text = self._prepare_contact_text(contact)
            
            # Análises específicas para atendentes
            analysis = {
                'contact_name': contact_name,
                'total_messages': len(messages),
                'message_types': self._count_message_types(messages),
                'conversation_duration': self._calculate_conversation_duration(messages),
                'subject_analysis': self._analyze_subject(contact_text, contact_name),
                'sentiment_analysis': self._analyze_sentiment(contact_text, contact_name),
                'communication_style': self._analyze_communication_style(contact_text, contact_name),
                'service_quality': self._analyze_service_quality(contact_text, contact_name),
                'key_topics': self._extract_key_topics(contact_text, contact_name),
                'action_items': self._extract_action_items(contact_text, contact_name),
                'customer_satisfaction': self._analyze_customer_satisfaction(contact_text, contact_name)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Erro ao analisar contato {contact.get('contact_name', 'Desconhecido')}: {e}")
            return None
    
    def _prepare_contact_text(self, contact: Dict) -> str:
        """Preparar texto da conversa com um contato específico"""
        contact_name = contact.get('contact_name', 'Desconhecido')
        messages = contact.get('messages', [])
        
        text_parts = [f"=== Conversa com {contact_name} ==="]
        
        for message in messages:
            text = message.get('text', '')
            timestamp = message.get('timestamp', '')
            message_type = message.get('message_type', 'text')
            
            if text:
                prefix = f"[{timestamp}] " if timestamp else ""
                if message_type == 'audio':
                    prefix += "[ÁUDIO] "
                
                text_parts.append(f"{prefix}{text}")
        
        return "\n".join(text_parts)
    
    def _count_message_types(self, messages: List[Dict]) -> Dict[str, int]:
        """Contar tipos de mensagens"""
        types = {'text': 0, 'audio': 0, 'total': len(messages)}
        
        for message in messages:
            msg_type = message.get('message_type', 'text')
            if msg_type in types:
                types[msg_type] += 1
        
        return types
    
    def _calculate_conversation_duration(self, messages: List[Dict]) -> Dict[str, Any]:
        """Calcular duração da conversa"""
        if not messages:
            return {'duration_minutes': 0, 'first_message': None, 'last_message': None}
        
        timestamps = [msg.get('timestamp') for msg in messages if msg.get('timestamp')]
        
        if len(timestamps) < 2:
            return {'duration_minutes': 0, 'first_message': timestamps[0] if timestamps else None, 'last_message': timestamps[0] if timestamps else None}
        
        try:
            from datetime import datetime
            first = datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))
            last = datetime.fromisoformat(timestamps[-1].replace('Z', '+00:00'))
            duration = (last - first).total_seconds() / 60
            
            return {
                'duration_minutes': round(duration, 1),
                'first_message': timestamps[0],
                'last_message': timestamps[-1]
            }
        except:
            return {'duration_minutes': 0, 'first_message': timestamps[0], 'last_message': timestamps[-1]}
    
    def _analyze_subject(self, contact_text: str, contact_name: str) -> Dict[str, Any]:
        """Analisar assunto principal da conversa"""
        prompt = f"""
Analise esta conversa de atendimento e identifique o assunto principal e contexto.

Conversa:
{contact_text}

Instruções:
- Identifique o assunto principal da conversa
- Classifique o tipo de atendimento (vendas, suporte, reclamação, etc.)
- Identifique o produto/serviço em questão
- Determine a urgência (alta, média, baixa)
- Identifique se é primeira interação ou follow-up

Responda em formato JSON:
{{
    "main_subject": "assunto principal",
    "service_type": "tipo de atendimento",
    "product_service": "produto/serviço",
    "urgency": "alta/media/baixa",
    "interaction_type": "primeira/retorno",
    "context": "contexto adicional"
}}
"""
        
        try:
            response = self.llama_service._call_ollama(prompt)
            # Tentar extrair JSON da resposta
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "main_subject": "Não identificado",
                    "service_type": "Não identificado",
                    "product_service": "Não identificado",
                    "urgency": "média",
                    "interaction_type": "primeira",
                    "context": response[:200] + "..." if len(response) > 200 else response
                }
        except Exception as e:
            self.logger.error(f"Erro na análise de assunto: {e}")
            return {
                "main_subject": "Erro na análise",
                "service_type": "Erro na análise",
                "product_service": "Erro na análise",
                "urgency": "média",
                "interaction_type": "primeira",
                "context": str(e)
            }
    
    def _analyze_sentiment(self, contact_text: str, contact_name: str) -> Dict[str, Any]:
        """Analisar sentimento da conversa"""
        prompt = f"""
Analise o sentimento e tom desta conversa de atendimento.

Conversa:
{contact_text}

Instruções:
- Analise o sentimento geral (positivo, neutro, negativo)
- Identifique emoções específicas (satisfação, frustração, urgência, etc.)
- Avalie o tom do cliente
- Avalie o tom do atendente
- Identifique pontos de tensão ou satisfação

Responda em formato JSON:
{{
    "overall_sentiment": "positivo/neutro/negativo",
    "sentiment_score": 0.0-1.0,
    "customer_emotions": ["emoção1", "emoção2"],
    "customer_tone": "descrição do tom",
    "agent_tone": "descrição do tom",
    "tension_points": ["ponto1", "ponto2"],
    "satisfaction_indicators": ["indicador1", "indicador2"]
}}
"""
        
        try:
            response = self.llama_service._call_ollama(prompt)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "overall_sentiment": "neutro",
                    "sentiment_score": 0.5,
                    "customer_emotions": ["neutro"],
                    "customer_tone": "neutro",
                    "agent_tone": "profissional",
                    "tension_points": [],
                    "satisfaction_indicators": []
                }
        except Exception as e:
            self.logger.error(f"Erro na análise de sentimento: {e}")
            return {
                "overall_sentiment": "neutro",
                "sentiment_score": 0.5,
                "customer_emotions": ["erro"],
                "customer_tone": "erro na análise",
                "agent_tone": "erro na análise",
                "tension_points": [],
                "satisfaction_indicators": []
            }
    
    def _analyze_communication_style(self, contact_text: str, contact_name: str) -> Dict[str, Any]:
        """Analisar estilo de comunicação"""
        prompt = f"""
Analise o estilo de comunicação nesta conversa de atendimento.

Conversa:
{contact_text}

Instruções:
- Avalie a clareza das comunicações
- Identifique o nível de formalidade
- Analise a proatividade do atendente
- Verifique se houve follow-up adequado
- Identifique qualidade das explicações
- Avalie tempo de resposta (se possível)

Responda em formato JSON:
{{
    "communication_clarity": "excelente/bom/regular/ruim",
    "formality_level": "formal/informal/adequado",
    "agent_proactivity": "alta/média/baixa",
    "follow_up_quality": "excelente/bom/regular/inexistente",
    "explanation_quality": "excelente/bom/regular/ruim",
    "response_efficiency": "rápido/adequado/lento",
    "communication_highlights": ["ponto1", "ponto2"],
    "improvement_areas": ["área1", "área2"]
}}
"""
        
        try:
            response = self.llama_service._call_ollama(prompt)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "communication_clarity": "bom",
                    "formality_level": "adequado",
                    "agent_proactivity": "média",
                    "follow_up_quality": "bom",
                    "explanation_quality": "bom",
                    "response_efficiency": "adequado",
                    "communication_highlights": [],
                    "improvement_areas": []
                }
        except Exception as e:
            self.logger.error(f"Erro na análise de comunicação: {e}")
            return {
                "communication_clarity": "erro",
                "formality_level": "erro",
                "agent_proactivity": "erro",
                "follow_up_quality": "erro",
                "explanation_quality": "erro",
                "response_efficiency": "erro",
                "communication_highlights": [],
                "improvement_areas": []
            }
    
    def _analyze_service_quality(self, contact_text: str, contact_name: str) -> Dict[str, Any]:
        """Analisar qualidade do atendimento"""
        prompt = f"""
Avalie a qualidade do atendimento nesta conversa.

Conversa:
{contact_text}

Instruções:
- Avalie se o problema foi resolvido
- Verifique se o atendente foi empático
- Analise se houve proatividade em oferecer soluções
- Verifique conhecimento técnico demonstrado
- Avalie se o atendimento foi personalizado
- Identifique se houve esforço para reter o cliente

Responda em formato JSON:
{{
    "problem_resolved": "sim/parcialmente/não",
    "empathy_level": "alta/média/baixa",
    "solution_proactivity": "alta/média/baixa",
    "technical_knowledge": "excelente/bom/regular/insuficiente",
    "personalization": "alta/média/baixa",
    "retention_effort": "alta/média/baixa",
    "service_rating": 1-10,
    "strengths": ["força1", "força2"],
    "weaknesses": ["fraqueza1", "fraqueza2"]
}}
"""
        
        try:
            response = self.llama_service._call_ollama(prompt)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "problem_resolved": "não identificado",
                    "empathy_level": "média",
                    "solution_proactivity": "média",
                    "technical_knowledge": "bom",
                    "personalization": "média",
                    "retention_effort": "média",
                    "service_rating": 7,
                    "strengths": [],
                    "weaknesses": []
                }
        except Exception as e:
            self.logger.error(f"Erro na análise de qualidade: {e}")
            return {
                "problem_resolved": "erro",
                "empathy_level": "erro",
                "solution_proactivity": "erro",
                "technical_knowledge": "erro",
                "personalization": "erro",
                "retention_effort": "erro",
                "service_rating": 0,
                "strengths": [],
                "weaknesses": []
            }
    
    def _extract_key_topics(self, contact_text: str, contact_name: str) -> List[str]:
        """Extrair tópicos principais da conversa"""
        prompt = f"""
Extraia os tópicos principais desta conversa de atendimento.

Conversa:
{contact_text}

Instruções:
- Liste os principais tópicos discutidos
- Máximo 5 tópicos
- Seja específico e conciso
- Foque em aspectos relevantes para o negócio

Responda apenas com uma lista, um tópico por linha:
"""
        
        try:
            response = self.llama_service._call_ollama(prompt)
            topics = [topic.strip() for topic in response.split('\n') if topic.strip()]
            return topics[:5]  # Limitar a 5 tópicos
        except Exception as e:
            self.logger.error(f"Erro na extração de tópicos: {e}")
            return ["Erro na análise de tópicos"]
    
    def _extract_action_items(self, contact_text: str, contact_name: str) -> List[Dict[str, str]]:
        """Extrair itens de ação da conversa"""
        prompt = f"""
Identifique ações ou compromissos assumidos nesta conversa de atendimento.

Conversa:
{contact_text}

Instruções:
- Identifique promessas feitas pelo atendente
- Identifique ações que o cliente precisa tomar
- Identifique prazos mencionados
- Identifique follow-ups necessários

Responda em formato JSON:
[
    {{"action": "descrição da ação", "responsible": "atendente/cliente", "deadline": "prazo se mencionado", "status": "pendente/em_andamento/concluído"}},
    ...
]
"""
        
        try:
            response = self.llama_service._call_ollama(prompt)
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return []
        except Exception as e:
            self.logger.error(f"Erro na extração de ações: {e}")
            return []
    
    def _analyze_customer_satisfaction(self, contact_text: str, contact_name: str) -> Dict[str, Any]:
        """Analisar satisfação do cliente"""
        prompt = f"""
Avalie a satisfação do cliente nesta conversa de atendimento.

Conversa:
{contact_text}

Instruções:
- Identifique indicadores de satisfação ou insatisfação
- Avalie se o cliente ficou satisfeito com a solução
- Identifique se há risco de churn
- Verifique se o cliente demonstrou intenção de compra/retorno
- Identifique feedback positivo ou negativo explícito

Responda em formato JSON:
{{
    "satisfaction_level": "muito_satisfeito/satisfeito/neutro/insatisfeito/muito_insatisfeito",
    "satisfaction_score": 1-10,
    "churn_risk": "baixo/médio/alto",
    "purchase_intent": "alta/média/baixa/inexistente",
    "explicit_feedback": "positivo/negativo/neutro/ausente",
    "loyalty_indicators": ["indicador1", "indicador2"],
    "satisfaction_factors": ["fator1", "fator2"]
}}
"""
        
        try:
            response = self.llama_service._call_ollama(prompt)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "satisfaction_level": "neutro",
                    "satisfaction_score": 5,
                    "churn_risk": "médio",
                    "purchase_intent": "média",
                    "explicit_feedback": "ausente",
                    "loyalty_indicators": [],
                    "satisfaction_factors": []
                }
        except Exception as e:
            self.logger.error(f"Erro na análise de satisfação: {e}")
            return {
                "satisfaction_level": "erro",
                "satisfaction_score": 0,
                "churn_risk": "erro",
                "purchase_intent": "erro",
                "explicit_feedback": "erro",
                "loyalty_indicators": [],
                "satisfaction_factors": []
            }
    
    def _generate_overall_analysis(self, contact_analyses: List[Dict], conversation_data: Dict) -> Dict[str, Any]:
        """Gerar análise geral da conversa"""
        if not contact_analyses:
            return {"error": "Nenhuma análise de contato disponível"}
        
        # Agregar dados de todas as análises
        total_messages = sum(ca['total_messages'] for ca in contact_analyses)
        total_duration = sum(ca['conversation_duration']['duration_minutes'] for ca in contact_analyses)
        
        # Calcular médias
        avg_sentiment_scores = [ca['sentiment_analysis']['sentiment_score'] for ca in contact_analyses if 'sentiment_score' in ca['sentiment_analysis']]
        avg_sentiment = sum(avg_sentiment_scores) / len(avg_sentiment_scores) if avg_sentiment_scores else 0.5
        
        service_ratings = [ca['service_quality']['service_rating'] for ca in contact_analyses if 'service_rating' in ca['service_quality']]
        avg_service_rating = sum(service_ratings) / len(service_ratings) if service_ratings else 5
        
        satisfaction_scores = [ca['customer_satisfaction']['satisfaction_score'] for ca in contact_analyses if 'satisfaction_score' in ca['customer_satisfaction']]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 5
        
        return {
            "total_contacts": len(contact_analyses),
            "total_messages": total_messages,
            "total_duration_minutes": round(total_duration, 1),
            "average_sentiment_score": round(avg_sentiment, 2),
            "average_service_rating": round(avg_service_rating, 1),
            "average_satisfaction_score": round(avg_satisfaction, 1),
            "conversation_summary": f"Conversa com {len(contact_analyses)} contato(s), {total_messages} mensagens, {total_duration:.1f} minutos",
            "overall_quality": "excelente" if avg_service_rating >= 8 else "bom" if avg_service_rating >= 6 else "regular" if avg_service_rating >= 4 else "ruim"
        }
    
    def _generate_executive_summary(self, contact_analyses: List[Dict], overall_analysis: Dict) -> Dict[str, Any]:
        """Gerar resumo executivo"""
        summary_prompt = f"""
Gere um resumo executivo desta análise de atendimento.

Análises por contato: {len(contact_analyses)} contatos analisados
Análise geral: {overall_analysis}

Instruções:
- Gere um resumo executivo em português brasileiro
- Destaque os pontos principais
- Identifique oportunidades de melhoria
- Forneça recomendações práticas
- Máximo 300 palavras
- Seja objetivo e acionável

Resumo Executivo:
"""
        
        try:
            response = self.llama_service._call_ollama(summary_prompt)
            return {
                "executive_summary": response.strip(),
                "key_insights": [
                    f"Análise de {len(contact_analyses)} contatos",
                    f"Qualidade geral: {overall_analysis.get('overall_quality', 'não avaliada')}",
                    f"Nota média de serviço: {overall_analysis.get('average_service_rating', 0)}/10",
                    f"Satisfação média: {overall_analysis.get('average_satisfaction_score', 0)}/10"
                ],
                "recommendations": self._extract_recommendations(contact_analyses),
                "priority_actions": self._identify_priority_actions(contact_analyses)
            }
        except Exception as e:
            self.logger.error(f"Erro na geração do resumo executivo: {e}")
            return {
                "executive_summary": "Erro na geração do resumo",
                "key_insights": ["Erro na análise"],
                "recommendations": [],
                "priority_actions": []
            }
    
    def _extract_recommendations(self, contact_analyses: List[Dict]) -> List[str]:
        """Extrair recomendações baseadas nas análises"""
        recommendations = []
        
        # Analisar áreas de melhoria comuns
        improvement_areas = []
        for analysis in contact_analyses:
            if 'communication_style' in analysis and 'improvement_areas' in analysis['communication_style']:
                improvement_areas.extend(analysis['communication_style']['improvement_areas'])
        
        # Recomendações baseadas em padrões
        if any('clareza' in area.lower() for area in improvement_areas):
            recommendations.append("Melhorar clareza nas comunicações com clientes")
        
        if any('proatividade' in area.lower() for area in improvement_areas):
            recommendations.append("Aumentar proatividade na oferta de soluções")
        
        # Recomendações baseadas em satisfação
        low_satisfaction = [ca for ca in contact_analyses if ca.get('customer_satisfaction', {}).get('satisfaction_score', 5) < 6]
        if low_satisfaction:
            recommendations.append("Investigar casos de baixa satisfação do cliente")
        
        return recommendations[:5]  # Máximo 5 recomendações
    
    def _identify_priority_actions(self, contact_analyses: List[Dict]) -> List[Dict[str, str]]:
        """Identificar ações prioritárias"""
        priority_actions = []
        
        for analysis in contact_analyses:
            # Ações com prazo definido
            action_items = analysis.get('action_items', [])
            for action in action_items:
                if action.get('deadline') and action.get('status') == 'pendente':
                    priority_actions.append({
                        "action": action['action'],
                        "responsible": action['responsible'],
                        "deadline": action['deadline'],
                        "priority": "alta"
                    })
            
            # Casos de alta insatisfação
            if analysis.get('customer_satisfaction', {}).get('churn_risk') == 'alto':
                priority_actions.append({
                    "action": "Acompanhamento urgente para cliente com risco de churn",
                    "responsible": "supervisor",
                    "deadline": "24h",
                    "priority": "crítica"
                })
        
        return priority_actions[:10]  # Máximo 10 ações prioritárias
    
    def _save_contact_analysis(self, conversation_id: str, analysis_result: Dict):
        """Salvar análise no banco de dados"""
        try:
            # Salvar no MongoDB
            self.db_service.db.contact_analyses.update_one(
                {"conversation_id": conversation_id},
                {"$set": analysis_result},
                upsert=True
            )
            
            # Salvar também no documento da conversa
            self.db_service.db.diarios.update_one(
                {"_id": self.db_service.ObjectId(conversation_id)},
                {"$set": {"contact_analysis": analysis_result}}
            )
            
            self.logger.info(f"✅ Análise de contatos salva para conversa {conversation_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar análise de contatos: {e}")
    
    def get_contact_analysis(self, conversation_id: str) -> Optional[Dict]:
        """Buscar análise de contatos existente"""
        try:
            analysis = self.db_service.db.contact_analyses.find_one({"conversation_id": conversation_id})
            return analysis
        except Exception as e:
            self.logger.error(f"Erro ao buscar análise de contatos: {e}")
            return None
    
    def analyze_multiple_conversations(self, conversation_ids: List[str]) -> Dict[str, Any]:
        """Analisar múltiplas conversas"""
        self._ensure_initialized()
        self._log_operation("análise múltipla", {"conversations_count": len(conversation_ids)})
        
        results = []
        successful = 0
        failed = 0
        
        for conv_id in conversation_ids:
            try:
                analysis = self.analyze_conversation_by_contacts(conv_id)
                if 'error' not in analysis:
                    results.append(analysis)
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                self.logger.error(f"Erro ao analisar conversa {conv_id}: {e}")
                failed += 1
        
        return {
            "total_conversations": len(conversation_ids),
            "successful_analyses": successful,
            "failed_analyses": failed,
            "results": results
        }
