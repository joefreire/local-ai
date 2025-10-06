# Script Unificado de Análise de Diários

Este diretório contém um script unificado para análise de diários completos ou contatos específicos usando Llama3.

## Script Principal

### `analyze_diary.py` ⭐ **ÚNICO SCRIPT NECESSÁRIO**

Script unificado que permite analisar:
- **Diário completo**: Todos os contatos de um diário
- **Contato específico**: Apenas um contato de um diário

## Uso

### Análise de Diário Completo
```bash
python analyze_diary.py <diary_id>
```

### Análise de Contato Específico
```bash
python analyze_diary.py <diary_id> <contact_name>
```

## Exemplos

### Python
```bash
# Analisar diário completo
python analyze_diary.py 68dfed5432af85dff60ffbc4

# Analisar apenas um contato específico
python analyze_diary.py 68dfed5432af85dff60ffbc4 "João Silva"
python analyze_diary.py 68dfed5432af85dff60ffbc4 "MARIA SANTOS"
```

### Windows (Batch)
```cmd
# Analisar diário completo
analyze.bat 68dfed5432af85dff60ffbc4

# Analisar contato específico
analyze.bat 68dfed5432af85dff60ffbc4 "João Silva"
```

## Saída

### 1. Resultado no Terminal
- Resumo da análise
- Estatísticas detalhadas
- Tópicos principais
- Análise de sentimento
- Insights importantes

### 2. Arquivo JSON
O resultado completo é salvo em `testes/results/` com nome:
- `analysis_{diary_id}_complete_{timestamp}.json` (diário completo)
- `analysis_{diary_id}_{contact_name}_{timestamp}.json` (contato específico)

### 3. Banco de Dados
A análise também é salva no MongoDB no campo `conversation_analysis`.

## Estrutura do JSON

```json
{
  "analysis_info": {
    "diary_id": "68dfed5432af85dff60ffbc4",
    "analysis_date": "2024-01-15T10:30:00",
    "scope": "diario_completo",
    "model_used": "llama3.2:3b"
  },
  "diary_info": {
    "user_name": "João Silva",
    "date": "15/01/2024",
    "total_contacts": 5,
    "analyzed_contact": "Todos os contatos"
  },
  "analysis": {
    "summary": {
      "result": "Resumo da conversa...",
      "prompt": "Prompt completo enviado para Llama3...",
      "success": true
    },
    "topics": {
      "result": ["trabalho", "família", "finanças"],
      "prompt": "Prompt completo enviado para Llama3...",
      "success": true
    },
    "sentiment": {
      "result": {
        "overall_sentiment": "positivo",
        "confidence": 0.8,
        "emotions": ["satisfação", "curiosidade"]
      },
      "prompt": "Prompt completo enviado para Llama3...",
      "success": true
    },
    "insights": {
      "result": ["Insight 1", "Insight 2"],
      "prompt": "Prompt completo enviado para Llama3...",
      "success": true
    },
    "conversation_stats": {
      "total_contacts": 5,
      "total_messages": 45,
      "audio_messages": 8,
      "text_messages": 37,
      "audio_percentage": 17.8
    }
  },
  "detailed_stats": {
    "total_messages": 45,
    "total_audio_messages": 8,
    "total_text_messages": 37,
    "overall_audio_percentage": 17.8,
    "contacts_breakdown": [
      {
        "contact_name": "João Silva",
        "total_messages": 15,
        "audio_messages": 3,
        "text_messages": 12,
        "audio_percentage": 20.0
      }
    ]
  },
  "raw_data": {
    "conversation_id": "68dfed5432af85dff60ffbc4",
    "user_name": "João Silva",
    "contacts": [...]
  }
}
```

## Pré-requisitos

1. **MongoDB** rodando com dados das conversas
2. **Ollama** rodando com modelo Llama3
3. **Variáveis de ambiente** configuradas no arquivo `.env`

## Configuração

Certifique-se de que o arquivo `.env` está configurado:

```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=dashboard_whatsapp
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

## Fluxo de Análise

1. **Verificar conexões** (MongoDB + Ollama)
2. **Buscar dados do diário** no MongoDB
3. **Filtrar contato** (se especificado)
4. **Executar análise** com Llama3
5. **Criar resultado completo** com estatísticas
6. **Salvar JSON** em `testes/results/`
7. **Salvar no banco** MongoDB
8. **Exibir resumo** no terminal

## Troubleshooting

### Erro de Conexão MongoDB
```
❌ MongoDB: [Errno 111] Connection refused
```
- Verifique se o MongoDB está rodando
- Confirme a URL no arquivo `.env`

### Erro de Conexão Ollama
```
❌ Ollama: Connection refused
```
- Verifique se o Ollama está rodando: `ollama list`
- Confirme a URL no arquivo `.env`
- Baixe o modelo: `ollama pull llama3.2:3b`

### Diário Não Encontrado
```
❌ Diário não encontrado
```
- Verifique se o ID do diário está correto
- Confirme se há dados no MongoDB

### Contato Não Encontrado
```
❌ Contato 'Nome' não encontrado
```
- Verifique se o nome do contato está correto
- O nome é case-sensitive
- Use aspas se o nome contém espaços

## Exemplo Completo

```bash
# 1. Analisar diário completo
python analyze_diary.py 68dfed5432af85dff60ffbc4

# Saída esperada:
# 🚀 Iniciando análise de diário
#    Diário ID: 68dfed5432af85dff60ffbc4
#    Escopo: Diário completo
# ✅ Ollama conectado - Modelo: llama3.2:3b
# ✅ Diário encontrado:
#    Usuário: João Silva
#    Data: 15/01/2024
#    Contatos: 5
# 🧠 Executando análise...
# ✅ Análise concluída!
# 💾 Resultado salvo: testes/results/analysis_68dfed5432af85dff60ffbc4_complete_20240115_103000.json
# 🎉 Análise concluída com sucesso!
```

## Funcionalidades Avançadas

### 🎯 **Análise com Contexto Completo**

O sistema agora inclui:

- 📝 **Transcrições de Áudio**: Mensagens de áudio são automaticamente transcritas e incluídas como texto
- 🖼️ **Análise de Imagens**: Imagens são analisadas e descrições incluídas no contexto
- 📅 **Contexto Histórico**: Mensagens dos últimos 7 dias do mesmo usuário para contexto
- 🔍 **Prompts Completos**: Todos os prompts enviados para a Llama3 são incluídos no JSON

### 📊 **Tipos de Mensagem Suportados**

- **text**: Mensagens de texto normais
- **audio_transcribed**: Áudios com transcrição disponível
- **image_analyzed**: Imagens com análise disponível
- **audio**: Áudios sem transcrição (marcados como [ÁUDIO])
- **image**: Imagens sem análise (marcadas como [IMAGEM])

### 🕒 **Contexto Histórico**

- Busca automaticamente conversas dos últimos 7 dias do mesmo usuário
- Máximo de 5 conversas históricas e 50 mensagens
- Incluído no prompt como "CONTEXTO HISTÓRICO"
- Ajuda a entender padrões comportamentais e evolução da conversa

## Prompts Incluídos

Cada análise agora inclui **todos os prompts completos** que foram enviados para a Llama3:

- 📝 **Prompt do Resumo**: Instruções para gerar resumo conciso
- 🏷️ **Prompt dos Tópicos**: Instruções para extrair tópicos principais
- 😊 **Prompt do Sentimento**: Instruções para análise emocional
- 💡 **Prompt dos Insights**: Instruções para gerar insights comportamentais

### Estrutura dos Prompts no JSON:
```json
{
  "summary": {
    "result": "Resumo gerado pela IA...",
    "prompt": "Prompt completo enviado para Llama3...",
    "success": true
  }
}
```

### Vantagens dos Prompts Incluídos:
- ✅ **Transparência**: Você pode ver exatamente o que foi enviado para a IA
- ✅ **Debugging**: Identificar problemas nos prompts
- ✅ **Reprodutibilidade**: Replicar análises com prompts modificados
- ✅ **Auditoria**: Rastrear como cada resultado foi gerado
- ✅ **Otimização**: Melhorar prompts baseado nos resultados

## Vantagens do Script Unificado

- ✅ **Simplicidade**: Apenas um script para tudo
- ✅ **Flexibilidade**: Diário completo ou contato específico
- ✅ **Completude**: JSON com todos os dados e análises
- ✅ **Organização**: Arquivos salvos em `results/` com timestamp
- ✅ **Rastreabilidade**: Salva tanto em JSON quanto no banco
- ✅ **Estatísticas**: Análise detalhada por contato e geral
- ✅ **Prompts Incluídos**: Todos os prompts utilizados na análise