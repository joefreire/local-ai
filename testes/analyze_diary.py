#!/usr/bin/env python3
"""
Script unificado para análise de diários e contatos específicos
Uso: python analyze_diary.py <diary_id> [contact_name]
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Adicionar o diretório raiz ao path
root_path = str(Path(__file__).parent.parent)
sys.path.insert(0, root_path)

class DiaryAnalyzer:
    """Analisador de diários unificado"""
    
    def __init__(self):
        self.db_service = None
        self.analysis_service = None
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
    
    def initialize_services(self):
        """Inicializar serviços"""
        try:
            from src.services.database_service import DatabaseService
            from src.services.analysis_service import LlamaService
            
            self.db_service = DatabaseService()
            self.analysis_service = LlamaService()
            
            # Testar conexão Ollama
            print("🔍 Verificando conexão com Ollama...")
            connection_result = self.analysis_service.test_connection()
            if not connection_result['connected']:
                raise Exception(f"Ollama não disponível: {connection_result.get('error', 'Erro desconhecido')}")
            
            print(f"✅ Ollama conectado - Modelo: {connection_result['selected_model']}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao inicializar serviços: {e}")
            return False
    
    def get_diary_data(self, diary_id: str):
        """Buscar dados do diário"""
        try:
            print(f"📋 Buscando diário: {diary_id}")
            conversation_data = self.db_service.get_conversation_text_for_analysis(diary_id)
            
            if not conversation_data:
                raise Exception("Diário não encontrado")
            
            print(f"✅ Diário encontrado:")
            print(f"   Usuário: {conversation_data.get('user_name', 'Desconhecido')}")
            print(f"   Data: {conversation_data.get('date', 'Data não disponível')}")
            print(f"   Contatos: {len(conversation_data.get('contacts', []))}")
            
            return conversation_data
            
        except Exception as e:
            print(f"❌ Erro ao buscar diário: {e}")
            return None
    
    def filter_contact(self, conversation_data: dict, contact_name: str):
        """Filtrar contato específico"""
        print(f"🔍 Filtrando contato: {contact_name}")
        
        contacts = conversation_data.get('contacts', [])
        filtered_contacts = []
        
        for contact in contacts:
            contact_name_clean = contact.get('contact_name', '').strip()
            search_name_clean = contact_name.strip()
            
            # Comparar com diferentes variações
            if (contact_name_clean.lower() == search_name_clean.lower() or
                contact_name_clean == search_name_clean or
                contact_name_clean.startswith(search_name_clean) or
                search_name_clean in contact_name_clean):
                filtered_contacts.append(contact)
                print(f"✅ Contato encontrado: {contact.get('contact_name')}")
                print(f"   Mensagens: {len(contact.get('messages', []))}")
                break
        
        if not filtered_contacts:
            print(f"❌ Contato '{contact_name}' não encontrado")
            available_contacts = [c.get('contact_name', 'Sem nome') for c in contacts]
            print(f"   Contatos disponíveis: {', '.join(available_contacts)}")
            return None
        
        # Criar nova estrutura com apenas o contato filtrado
        filtered_data = conversation_data.copy()
        filtered_data['contacts'] = filtered_contacts
        filtered_data['analysis_scope'] = f"contato_{contact_name}"
        
        return filtered_data
    
    def analyze_conversation(self, conversation_data: dict):
        """Executar análise da conversa"""
        print("🧠 Executando análise...")
        
        try:
            analysis = self.analysis_service.analyze_conversation(conversation_data)
            
            if 'error' in analysis:
                raise Exception(f"Erro na análise: {analysis['error']}")
            
            print("✅ Análise concluída!")
            return analysis
            
        except Exception as e:
            print(f"❌ Erro na análise: {e}")
            return None
    
    def create_analysis_result(self, diary_id: str, conversation_data: dict, analysis: dict, contact_name: str = None):
        """Criar resultado completo da análise"""
        
        # Informações básicas
        result = {
            "analysis_info": {
                "diary_id": diary_id,
                "analysis_date": datetime.now().isoformat(),
                "scope": f"contato_{contact_name}" if contact_name else "diario_completo",
                "model_used": "llama3.2:3b"
            },
            "diary_info": {
                "user_name": conversation_data.get('user_name', 'Desconhecido'),
                "date": conversation_data.get('date', 'Data não disponível'),
                "total_contacts": len(conversation_data.get('contacts', [])),
                "analyzed_contact": contact_name if contact_name else "Todos os contatos"
            },
            "analysis": analysis,
            "raw_data": conversation_data
        }
        
        # Adicionar estatísticas detalhadas
        contacts = conversation_data.get('contacts', [])
        total_messages = 0
        total_audio_messages = 0
        
        contact_details = []
        for contact in contacts:
            messages = contact.get('messages', [])
            contact_total = len(messages)
            contact_audio = sum(1 for msg in messages if msg.get('message_type') == 'audio')
            
            total_messages += contact_total
            total_audio_messages += contact_audio
            
            contact_details.append({
                "contact_name": contact.get('contact_name', 'Desconhecido'),
                "total_messages": contact_total,
                "audio_messages": contact_audio,
                "text_messages": contact_total - contact_audio,
                "audio_percentage": (contact_audio / contact_total * 100) if contact_total > 0 else 0
            })
        
        result["detailed_stats"] = {
            "total_messages": total_messages,
            "total_audio_messages": total_audio_messages,
            "total_text_messages": total_messages - total_audio_messages,
            "overall_audio_percentage": (total_audio_messages / total_messages * 100) if total_messages > 0 else 0,
            "contacts_breakdown": contact_details
        }
        
        return result
    
    def save_result(self, result: dict, diary_id: str, contact_name: str = None):
        """Salvar resultado em JSON"""
        
        # Gerar nome do arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if contact_name:
            filename = f"analysis_{diary_id}_{contact_name}_{timestamp}.json"
        else:
            filename = f"analysis_{diary_id}_complete_{timestamp}.json"
        
        filepath = self.results_dir / filename
        
        try:
            # Função para converter datetime para string
            def json_serial(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=json_serial)
            
            print(f"💾 Resultado salvo: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")
            return None
    
    def display_summary(self, result: dict):
        """Exibir resumo dos resultados"""
        print("\n" + "="*60)
        print("📊 RESUMO DA ANÁLISE")
        print("="*60)
        
        # Informações básicas
        diary_info = result.get('diary_info', {})
        analysis_info = result.get('analysis_info', {})
        
        print(f"\n📋 INFORMAÇÕES:")
        print(f"   Diário ID: {analysis_info.get('diary_id', 'N/A')}")
        print(f"   Usuário: {diary_info.get('user_name', 'N/A')}")
        print(f"   Data: {diary_info.get('date', 'N/A')}")
        print(f"   Escopo: {diary_info.get('analyzed_contact', 'N/A')}")
        print(f"   Data da análise: {analysis_info.get('analysis_date', 'N/A')}")
        
        # Estatísticas
        stats = result.get('detailed_stats', {})
        print(f"\n📈 ESTATÍSTICAS:")
        print(f"   Total de mensagens: {stats.get('total_messages', 0)}")
        print(f"   Mensagens de áudio: {stats.get('total_audio_messages', 0)}")
        print(f"   Mensagens de texto: {stats.get('total_text_messages', 0)}")
        print(f"   % de áudios: {stats.get('overall_audio_percentage', 0):.1f}%")
        
        # Informações sobre transcrições e contexto
        raw_data = result.get('raw_data', {})
        historical_context = raw_data.get('historical_context', [])
        
        print(f"\n🔍 CONTEXTO E TRANSCRIÇÕES:")
        print(f"   Mensagens históricas (7 dias): {len(historical_context)}")
        
        # Contar tipos de mensagem
        audio_transcribed = 0
        image_analyzed = 0
        for contact in raw_data.get('contacts', []):
            for message in contact.get('messages', []):
                if message.get('has_transcription'):
                    audio_transcribed += 1
                if message.get('has_image_analysis'):
                    image_analyzed += 1
        
        print(f"   Áudios transcritos: {audio_transcribed}")
        print(f"   Imagens analisadas: {image_analyzed}")
        
        # Análise
        analysis = result.get('analysis', {})
        
        # Resumo
        summary_data = analysis.get('summary', {})
        if isinstance(summary_data, dict):
            summary = summary_data.get('result', 'Resumo não disponível')
        else:
            summary = summary_data
        
        print(f"\n📝 RESUMO:")
        if len(summary) > 300:
            summary = summary[:300] + "..."
        print(summary)
        
        # Tópicos
        topics_data = analysis.get('topics', [])
        if isinstance(topics_data, dict):
            topics = topics_data.get('result', [])
        else:
            topics = topics_data
        
        if topics:
            print(f"\n🏷️ TÓPICOS PRINCIPAIS:")
            for i, topic in enumerate(topics[:3], 1):
                print(f"   {i}. {topic}")
        
        # Sentimento
        sentiment_data = analysis.get('sentiment', {})
        if isinstance(sentiment_data, dict) and 'result' in sentiment_data:
            sentiment = sentiment_data.get('result', {})
        else:
            sentiment = sentiment_data
        
        if sentiment:
            print(f"\n😊 SENTIMENTO:")
            print(f"   Geral: {sentiment.get('overall_sentiment', 'N/A')}")
            print(f"   Confiança: {sentiment.get('confidence', 0):.2f}")
        
        # Insights
        insights_data = analysis.get('insights', [])
        if isinstance(insights_data, dict):
            insights = insights_data.get('result', [])
        else:
            insights = insights_data
        
        if insights:
            print(f"\n💡 INSIGHTS:")
            for i, insight in enumerate(insights[:2], 1):
                if len(insight) > 100:
                    insight = insight[:100] + "..."
                print(f"   {i}. {insight}")
        
        # Mostrar prompts se disponíveis
        print(f"\n🔍 PROMPTS UTILIZADOS:")
        prompts_shown = 0
        
        if isinstance(summary_data, dict) and 'prompt' in summary_data:
            print(f"   📝 Prompt do Resumo: {len(summary_data['prompt'])} caracteres")
            prompts_shown += 1
        
        if isinstance(topics_data, dict) and 'prompt' in topics_data:
            print(f"   🏷️ Prompt dos Tópicos: {len(topics_data['prompt'])} caracteres")
            prompts_shown += 1
        
        if isinstance(sentiment_data, dict) and 'prompt' in sentiment_data:
            print(f"   😊 Prompt do Sentimento: {len(sentiment_data['prompt'])} caracteres")
            prompts_shown += 1
        
        if isinstance(insights_data, dict) and 'prompt' in insights_data:
            print(f"   💡 Prompt dos Insights: {len(insights_data['prompt'])} caracteres")
            prompts_shown += 1
        
        if prompts_shown == 0:
            print(f"   ⚠️ Prompts não disponíveis (formato antigo)")
        else:
            print(f"   ✅ {prompts_shown} prompts incluídos no JSON")
        
        print("="*60)
    
    def analyze(self, diary_id: str, contact_name: str = None):
        """Executar análise completa"""
        print(f"🚀 Iniciando análise de diário")
        print(f"   Diário ID: {diary_id}")
        if contact_name:
            print(f"   Contato: {contact_name}")
        else:
            print(f"   Escopo: Diário completo")
        print("-" * 50)
        
        # Inicializar serviços
        if not self.initialize_services():
            return None
        
        # Buscar dados do diário
        conversation_data = self.get_diary_data(diary_id)
        if not conversation_data:
            return None
        
        # Filtrar contato se especificado
        if contact_name:
            conversation_data = self.filter_contact(conversation_data, contact_name)
            if not conversation_data:
                return None
        
        # Executar análise
        analysis = self.analyze_conversation(conversation_data)
        if not analysis:
            return None
        
        # Criar resultado completo
        result = self.create_analysis_result(diary_id, conversation_data, analysis, contact_name)
        
        # Salvar resultado
        filepath = self.save_result(result, diary_id, contact_name)
        if not filepath:
            return None
        
        # Exibir resumo
        self.display_summary(result)
        
        # Salvar também no banco de dados
        print(f"\n💾 Salvando análise no banco de dados...")
        success = self.db_service.save_conversation_analysis(diary_id, analysis)
        print("✅ Análise salva no banco!" if success else "⚠️ Erro ao salvar no banco")
        
        return {
            "result": result,
            "filepath": filepath,
            "success": True
        }
    
    def close(self):
        """Fechar conexões"""
        try:
            if self.db_service:
                self.db_service.close()
            if self.analysis_service:
                self.analysis_service.close()
        except:
            pass

def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("❌ Uso: python analyze_diary.py <diary_id> [contact_name]")
        print("\nExemplos:")
        print("  python analyze_diary.py 68dfed5432af85dff60ffbc4")
        print("  python analyze_diary.py 68dfed5432af85dff60ffbc4 João Silva")
        print("\nO arquivo JSON será salvo em: testes/results/")
        return 1
    
    diary_id = sys.argv[1]
    contact_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    analyzer = DiaryAnalyzer()
    
    try:
        result = analyzer.analyze(diary_id, contact_name)
        
        if result:
            print(f"\n🎉 Análise concluída com sucesso!")
            print(f"📁 Arquivo salvo: {result['filepath']}")
            return 0
        else:
            print(f"\n❌ Falha na análise")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n👋 Análise interrompida pelo usuário")
        return 1
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        analyzer.close()

if __name__ == "__main__":
    sys.exit(main())
