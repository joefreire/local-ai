# 🎙️ Sistema de Transcrição WhatsApp - Completo

Sistema completo e otimizado para processar **milhares de áudios por dia** de conversas do WhatsApp Business, integrado com sistema Laravel existente.

**Abordagem Local**: Sem Docker, sem APIs web complexas - apenas scripts Python diretos e organizados.

## 📋 Visão Geral

Este sistema processa diários de conversas do WhatsApp que são populados pelo sistema Laravel, transcrevendo áudios e fazendo análise inteligente das conversas.

### 🔄 Fluxo de Dados

```
Sistema Laravel → MongoDB → Sistema Python → Análise Completa
     ↓              ↓           ↓              ↓
  Popula        Armazena    Processa      Salva
  Diários       Dados       Áudios        Resultados
```

## ✨ Características

### 🎵 Processamento de Áudios
- **Whisper Local**: Transcrição de alta qualidade em português
- **Download automático** de áudios das URLs
- **Transcrição com Whisper** (GPU otimizada)
- **Batch processing** para eficiência máxima
- **Controle de status** no MongoDB

### 🧠 Análise de Conversas 
- **Análise por contato individual** - Cada conversa é analisada separadamente
- **Resumo global do diário** - Feedback consolidado baseado em todas as conversas
- **Extração de tópicos** principais por contato
- **Análise de sentimentos** individual e global
- **Insights inteligentes** sobre padrões comportamentais
- **Contexto histórico** - Considera conversas dos últimos 7 dias

### 📊 Organização e Controle
- **Organização**: Arquivos por diário e mensagem
- **Processamento Modular**: Download → Transcrição → Sincronização
- **MongoDB**: Integração com diários existentes do Laravel
- **Instalação Simples**: Script automatizado para ambiente local
- **Rastreamento**: Campo `audio_transcriptions` para controle

### 📈 Monitoramento
- **Métricas em tempo real**
- **Alertas automáticos**
- **Estatísticas de performance**
- **Logs detalhados**

## 📁 Estrutura do Projeto

```
transcrever_audio/
├── check_pending.py         # Verificar diários pendentes
├── cli.py                   # CLI original (compatibilidade)
├── cli_refactored.py        # CLI refatorado (recomendado)
├── ultra_transcribe.py      # Transcritor principal
├── install.py              # Instalação automatizada
├── test_system.py          # Testes do sistema
├── manage_system.py        # Gerenciamento do sistema
├── requirements.txt        # Dependências básicas
├── requirements_optimized.txt  # Dependências otimizadas
├── .env                    # Configurações (crie a partir do .env.example)
├── src/                    # Código fonte organizado
│   ├── services/          # Services (DRY, KISS, Single Responsibility)
│   │   ├── base_service.py
│   │   ├── audio_service.py
│   │   ├── database_service.py
│   │   ├── download_service.py
│   │   ├── processing_service.py
│   │   └── analysis_service.py
│   ├── config.py          # Configurações
│   └── api_simple.py      # API simples (opcional)
├── downloads/             # Arquivos organizados por ID
│   ├── {diario_id}/
│   │   ├── {message_id}.oga
│   │   ├── {message_id}_transcription.json
│   │   └── ...
├── logs/                  # Logs do sistema
└── temp/                  # Arquivos temporários
```

## 🏗️ Arquitetura do Sistema

### 📊 Estrutura de Dados (MongoDB)

O sistema trabalha com a coleção `diarios` que contém:

#### 📄 Documento Diário
```javascript
{
  "_id": ObjectId("68dff3cd5871f418cb04a3f2"),
  "user_id": 438,
  "user_name": "ADRIEL CARDOZO DA SILVA",
  "user_email": "adriel.cardozo@wz.com.br",
  "company_id": 3,
  "company_name": "UNICESUMAR",
  "date": "2025-10-02T00:00:00.000Z",
  "date_formatted": "02/10/2025",
  "day_of_week": "quinta-feira",
  
  // Status de processamento
  "status_diario": "completed",
  "status_audios": "pending",        // ← Nosso foco
  "analysis_status": "pending",
  
  // Estatísticas
  "total_messages": 64,
  "total_contacts": 7,
  "audio_messages": 2,               // ← Áudios para transcrever
  "media_messages": 9,
  
  // Novo campo de controle
  "audio_transcriptions": {
    "total_audios": 5,
    "transcribed_audios": 5,
    "pending_audios": 0,
    "transcription_status": "completed",
    "last_updated": "2025-10-03T14:30:00"
  },
  
  // Conversas
  "contacts": [
    {
      "contact_name": "Tayna",
      "contact_phone": "553399639866",
      "ticket_id": 28322,
      "messages": [
        {
          "_id": "3A6E7CBC0A08D764BA55",
          "media_type": "audio",           // ← Tipo de mídia
          "media_url": "1759445969529.oga",
          "direct_media_url": "https://api-nova.wzcontrole.com.br/public/1759445969529.oga",
          "is_audio": false,               // ← Campo para identificar áudio
          
          // Campo de transcrição
          "audio_transcription": "Texto transcrito...",
          "transcription_data": { /* objeto completo */ },
          "transcription_status": "completed",
          "created_at": "2025-10-02 19:59:29"
        }
      ]
    }
  ]
}
```

#### 🎯 Campos Importantes para Processamento

**Identificação de Áudios:**
- `media_type: "audio"`
- `direct_media_url` (URL para download)
- `is_audio: false` (campo inconsistente, usar `media_type`)

**URLs de Download:**
- `direct_media_url` (prioritário)
- `download_url` (alternativo)
- `media_url` (fallback)

**Status de Processamento:**
- `status_audios`: "pending" → "processing" → "completed"/"error"

## 🚀 Instalação e Configuração

### 1. Pré-requisitos

#### Hardware
- **GPU NVIDIA RTX 4070** (8.6GB VRAM) - Recomendado
- **16GB+ RAM**
- **SSD** para armazenamento rápido

#### Software
- **Python 3.8+** (3.11+ recomendado)
- **CUDA 12.1+** (para GPU)
- **FFmpeg** (para processamento de áudio)
- **MongoDB Atlas** ou local
- **Ollama** (opcional para análise)

### 2. Instalação Automatizada

```powershell
# 1. Clone o repositório
git clone <seu-repositorio>
cd transcrever_audio

# 2. Execute o instalador
python install.py
```

O script `install.py` irá:
- ✅ Verificar versão do Python
- ✅ Verificar se FFmpeg está instalado
- ✅ Instalar dependências Python necessárias
- ✅ Criar estrutura de diretórios
- ✅ Verificar configurações

### 3. Instalação Manual

```powershell
# Clonar repositório
git clone <seu-repositorio>
cd transcrever_audio

# Copiar configurações
copy env_example.txt .env
# Editar .env com suas configurações

# Instalar dependências
pip install -r requirements_optimized.txt

# Criar diretórios
mkdir downloads, logs, temp
```

### 4. Configuração (.env)

```bash
# === MONGODB (Obrigatório) ===
MONGODB_URL=mongodb+srv://usuario:senha@cluster.mongodb.net/
MONGODB_DATABASE=dashboard_whatsapp

# === WHISPER ===
WHISPER_MODEL=large-v3          # tiny, base, small, medium, large, large-v3, turbo
WHISPER_LANGUAGE=pt

# === GPU SETTINGS (RTX 4070) ===
GPU_BATCH_SIZE=4               # 4 áudios por batch
GPU_MEMORY_FRACTION=0.8        # 80% da VRAM

# === OLLAMA (Análise de Conversas) ===
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# === PROCESSAMENTO ===
MAX_CONCURRENT_JOBS=8          # Workers paralelos
AUDIO_DOWNLOAD_TIMEOUT=60

# === LOGGING ===
LOG_LEVEL=INFO
```

### 5. FFmpeg

**Windows:**
```powershell
# Via Chocolatey
choco install ffmpeg

# Via Winget  
winget install FFmpeg

# Manual: https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg  # CentOS/RHEL
```

## 🎯 Uso Prático

### 1. Teste Completo do Sistema

```powershell
# Executar todos os testes
python test_system.py

# Criar arquivo de áudio de teste
python test_system.py create-test-audio
```

### 2. CLI Refatorado (Recomendado)

```powershell
# Ver ajuda completa
python cli_refactored.py help

# Testar componentes individuais
python cli_refactored.py test-mongodb
python cli_refactored.py test-gpu
python cli_refactored.py test-whisper
python cli_refactored.py test-ollama

# Executar todos os testes
python cli_refactored.py test-all

# Listar conversas pendentes
python cli_refactored.py list-pending 20

# Ver detalhes de uma conversa
python cli_refactored.py show-conversation 68dfed5c32af85df

# Processar conversa específica
python cli_refactored.py process-conversation 68dfed5c32af85df

# Processar arquivo de áudio individual
python cli_refactored.py process-file audio_files/teste.oga

# Iniciar processamento automático
python cli_refactored.py start-auto 60
```

### 3. CLI Original (Compatibilidade)

```powershell
# Verificar sistema
python cli.py test-all

# Listar conversas pendentes
python cli.py list-pending

# Processar arquivo individual
python cli.py process-file audio_files/teste.oga
```

### 4. Scripts Legados

```powershell
# Verificar diários pendentes
python check_pending.py

# Atualizar campo audio_transcriptions
python check_pending.py --update-transcriptions

# Criar diário de teste
python check_pending.py --create-test

# Processamento completo
python ultra_transcribe.py --limit 5

# Processamento modular
python ultra_transcribe.py --download-only --limit 10
python ultra_transcribe.py --transcribe-only
python ultra_transcribe.py --sync-db
```

### 5. Sistema de Gerenciamento (Opcional)

```powershell
# Verificar sistema
python manage_system.py check

# Iniciar processamento contínuo
python manage_system.py start

# Verificar status
python manage_system.py status

# Descobrir conversas pendentes
python manage_system.py discover

# Processar conversas específicas
python manage_system.py process 68dfed5c32af85df 68e00dc7f19afcb3

# Limpar conversas com erro
python manage_system.py cleanup

# Iniciar API web
python manage_system.py api
```

### 6. API Web (Opcional)

Acesse quando disponível:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Status**: http://localhost:8000/health

**Endpoints úteis:**
```powershell
GET  /health                    # Status do sistema
GET  /processing/status         # Status do processamento
GET  /conversations/pending     # Conversas pendentes
POST /conversations/{id}/process # Processar conversa
GET  /metrics                   # Métricas do sistema
```

## 📊 Exemplos de Uso Real

### Exemplo 1: Verificar Sistema

```powershell
# Teste completo
python cli_refactored.py test-all

# Saída esperada:
# 🗄️ Testando MongoDB...
# ✅ Conexão MongoDB OK
# 📊 Total de diários: 1250
# 🎵 Diários com áudio: 340
# ⏳ Diários pendentes: 45

# 🚀 Testando GPU...
# ✅ GPU: NVIDIA GeForce RTX 4070 (8.0GB)
# 💾 VRAM total: 8.0GB
# 🔧 Memória alocada: 0.1GB

# 🎙️ Testando Whisper...
# ✅ Modelo Whisper carregado
# ✅ Teste OK - Texto: Olá, como vai? Espero que esteja tudo bem...

# 🧠 Testando Ollama...
# ✅ Ollama conectado - Modelo llama3.1:8b disponível
```

### Exemplo 2: Processar Conversas

```powershell
# Listar pendentes
python cli_refactored.py list-pending 10

# Saída:
# 📋 Buscando 10 conversas pendentes...
# 📊 Encontradas 8 conversas pendentes:
# ID          Usuário              Status        Áudios   Data
# 68dff3cd    ADRIEL CARDOZO      pending       2        02/10/2025
# 68e00dc7    MARIA SILVA         pending       1        02/10/2025
# 68f1a2b3    JOÃO SANTOS         pending       3        03/10/2025

# Processar conversa específica
python cli_refactored.py process-conversation 68dff3cd5871f418cb04a3f2

# Saída:
# 🚀 Processando conversa: 68dff3cd
# ✅ Processamento concluído:
#    📊 Status: completed
#    🎵 Total de áudios: 2
#    ⬇️ Baixados: 2
#    🎙️ Transcritos: 2
#    ❌ Falhas: 0
#    🧠 Análise: Sim
```

### Exemplo 3: Processamento Automático

```powershell
# Iniciar processamento contínuo
python cli_refactored.py start-auto 30

# Saída:
# 🚀 Iniciando processamento automático (intervalo: 30s)...
# ✅ Processamento automático iniciado
# 💡 Use Ctrl+C para parar

# [A cada 30 segundos]
# 📋 Encontradas 5 conversas pendentes
# 🎵 Processando conversa 68dff3cd...
# ✅ Conversa 68dff3cd processada: completed
# 🎵 Processando conversa 68e00dc7...
# ✅ Conversa 68e00dc7 processada: completed
```

## 📊 Fluxo de Trabalho

### Abordagem Modular Recomendada

```mermaid
graph TD
    A[Verificar Pendentes] --> B[Download de Áudios]
    B --> C[Transcrição Local]
    C --> D[Sincronização MongoDB]
    D --> E[Análise de Conversas]
    
    A --> F[cli_refactored.py list-pending]
    B --> G[cli_refactored.py process-conversation]
    C --> H[Whisper GPU]
    D --> I[Database Service]
    E --> J[Ollama Analysis]
```

### Vantagens da Abordagem Modular

- **🔄 Retomada**: Continue de onde parou se houver interrupção
- **🎛️ Controle**: Processe apenas a etapa necessária
- **💾 Backup**: Arquivos locais preservados entre execuções
- **🐛 Debug**: Isole problemas específicos em cada etapa

## 📂 Organização de Arquivos

### Estrutura por Diário

```
downloads/
├── 68dfed5c32af85df/          # ID do diário
│   ├── 3A6E7CBC0A08D764BA55.oga      # Áudio da mensagem
│   ├── 3A6E7CBC0A08D764BA55_transcription.json  # Transcrição
│   ├── ACB55C020E3D410D0D58.oga      # Outro áudio
│   ├── ACB55C020E3D410D0D58_transcription.json
│   └── ...
└── 68e00dc7f19afcb3/          # Outro diário
    └── ...
```

### Formato da Transcrição

```json
{
  "text": "Texto transcrito completo",
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "Olá como vai"
    }
  ],
  "language": "pt",
  "confidence": 0.95,
  "duration": 5.2,
  "file_path": "/path/to/audio.oga",
  "transcribed_at": "2025-10-03T14:30:00"
}
```

## 📈 Performance Esperada

### RTX 4070 (8.6GB VRAM)

| Métrica | Valor |
|---------|-------|
| **Transcrição** | 50-100 áudios/minuto |
| **Análise** | 20-30 conversas/minuto |
| **Throughput** | 3000-6000 áudios/hora |
| **Latência** | <2min por áudio |

### Modelo Whisper

- **tiny**: Mais rápido, menor qualidade
- **base**: Equilibrado para testes
- **small**: Boa qualidade, velocidade razoável
- **medium**: Alta qualidade, mais lento
- **large**: Máxima qualidade, muito lento
- **large-v3**: **Recomendado** - melhor qualidade atual
- **turbo**: Qualidade alta, velocidade otimizada

### Configurações Otimizadas

```bash
# Para RTX 4070
WHISPER_MODEL=large-v3          # Melhor qualidade
GPU_BATCH_SIZE=4               # 4 áudios simultâneos
GPU_MEMORY_FRACTION=0.8        # 80% da VRAM
MAX_CONCURRENT_JOBS=8          # 8 workers paralelos

# Para GPU com menos VRAM
WHISPER_MODEL=base             # Modelo menor
GPU_BATCH_SIZE=2               # Batch menor
GPU_MEMORY_FRACTION=0.6        # Menos memória

# Para CPU apenas
WHISPER_MODEL=small            # Modelo pequeno
GPU_BATCH_SIZE=1               # Sem GPU
```

### Processamento em Lotes

```powershell
# Processar muitos diários em pequenos lotes
python ultra_transcribe.py --limit 5   # Lote pequeno
python ultra_transcribe.py --limit 10  # Lote médio
python ultra_transcribe.py --limit 20  # Lote grande
```

## 🔍 Estrutura de Resultados

### Transcrição de Áudio

```javascript
{
  "audio_transcription": "Olá, como vai? Espero que esteja tudo bem...",
  "transcription_data": {
    "text": "Olá, como vai? Espero que esteja tudo bem...",
    "segments": [
      {
        "start": 0.0,
        "end": 2.5,
        "text": "Olá, como vai?"
      }
    ],
    "language": "pt",
    "confidence": 0.95,
    "duration": 5.2,
    "transcribed_at": "2025-01-03T14:30:00"
  },
  "transcription_status": "completed"
}
```

### Análise de Conversa

```javascript
{
  "conversation_analysis": {
    "summary": "Conversa sobre solicitação de livros de anatomia...",
    "topics": ["educação", "livros", "polo universitário", "anatomia"],
    "sentiment": {
      "overall_sentiment": "positivo",
      "confidence": 0.85,
      "emotions": ["satisfação", "cordialidade"],
      "description": "Conversa cordial com tom positivo"
    },
    "insights": [
      "Cliente demonstrou interesse em material didático",
      "Atendente foi prestativo e ofereceu alternativas"
    ],
    "conversation_stats": {
      "total_contacts": 1,
      "total_messages": 30,
      "audio_messages": 1,
      "text_messages": 29,
      "audio_percentage": 3.33
    },
    "analyzed_at": "2025-01-03T14:30:00"
  }
}
```

## 🔧 Troubleshooting

### Problemas Comuns

#### 1. GPU não detectada
```powershell
# Testar GPU
python cli_refactored.py test-gpu

# Verificar CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Instalar PyTorch com CUDA
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### 2. MongoDB erro de conexão
```powershell
# Testar MongoDB
python cli_refactored.py test-mongodb

# Verificar configuração
cat .env | grep MONGODB

# Testar conexão
python check_pending.py
```

#### 3. Whisper não funciona
```powershell
# Testar Whisper
python cli_refactored.py test-whisper

# Criar arquivo de teste
python cli_refactored.py create-test-audio

# Instalar Whisper
pip install openai-whisper

# Verificar áudio baixado
ls downloads/{diario_id}/

# Tentar transcrição isolada
python ultra_transcribe.py --transcribe-only
```

#### 4. FFmpeg não encontrado
```powershell
# Verificar instalação
ffmpeg -version

# Instalar se necessário
choco install ffmpeg
```

#### 5. Ollama não conecta
```powershell
# Testar Ollama
python cli_refactored.py test-ollama

# Instalar Ollama
# https://ollama.ai/download

# Baixar modelo
ollama pull llama3.1:8b

# Iniciar servidor
ollama serve
```

#### 6. Dependências faltando
```powershell
# Executar teste completo
python test_system.py

# Instalar dependências
pip install -r requirements_optimized.txt
```

#### 7. Memória insuficiente
```bash
# Usar modelo menor
WHISPER_MODEL=small
```

## 📊 Monitoramento e Métricas

### Comandos de Monitoramento

```powershell
# Status do sistema
python cli_refactored.py test-all

# Listar conversas pendentes
python cli_refactored.py list-pending 100

# Verificar processamento
python cli_refactored.py show-conversation <id>

# Ver estatísticas detalhadas
python check_pending.py --limit 100

# Ver arquivos baixados
ls downloads/

# Ver logs
Get-Content logs/*.log | Select-Object -Last 50

# Ver logs em tempo real
Get-Content logs/*.log -Wait

# Ver últimos erros
Select-String "ERROR" logs/*.log | Select-Object -Last 10
```

### Métricas Importantes

- **Conversas pendentes**: Diários com `status_audios = "pending"`
- **Áudios por conversa**: Campo `audio_messages`
- **URLs válidas**: Verificar `direct_media_url`
- **Status de processamento**: `status_audios` e `analysis_status`

### Estatísticas

```powershell
# Total de arquivos baixados
Get-ChildItem downloads/ -Recurse -File | Measure-Object

# Total de transcrições
Get-ChildItem downloads/ -Recurse -Filter "*_transcription.json" | Measure-Object
```

### Limpeza

```powershell
# Limpar arquivos temporários
Remove-Item temp/* -Recurse -Force

# Limpar downloads específicos
Remove-Item downloads/{diario_id} -Recurse -Force
```

## 🚀 Integração com Laravel

### Modelo Laravel (Referência)

```php
// App\Models\Diario.php
class Diario extends Model
{
    protected $connection = 'mongodb';
    protected $collection = 'diarios';
    
    // Status possíveis
    const STATUS_AUDIOS_PENDING = 'pending';
    const STATUS_AUDIOS_PROCESSING = 'processing';
    const STATUS_AUDIOS_COMPLETED = 'completed';
    const STATUS_AUDIOS_ERROR = 'error';
    
    // Campos importantes
    protected $fillable = [
        'user_id', 'user_name', 'company_id',
        'date', 'date_formatted',
        'status_audios', 'audio_messages',
        'contacts', 'created_at', 'updated_at'
    ];
}
```

### Fluxo de Integração

1. **Laravel** popula diários no MongoDB
2. **Python** detecta diários com `status_audios = "pending"`
3. **Python** processa áudios e atualiza status
4. **Laravel** pode consultar resultados

## 🔧 Desenvolvimento

### Estrutura do Código

- `cli_refactored.py`: CLI refatorado com comandos intuitivos
- `cli.py`: CLI original (compatibilidade)
- `check_pending.py`: Verificação e controle de diários
- `ultra_transcribe.py`: Processamento principal de transcrição
- `install.py`: Instalação e verificação do ambiente
- `test_system.py`: Testes do sistema
- `src/services/`: Services organizados (DRY, KISS, Single Responsibility)

### Extensões

Para adicionar novas funcionalidades:

1. **Novos formatos de áudio**: Modificar `extract_audio_urls()`
2. **Outros provedores de transcrição**: Criar nova classe transcriber
3. **Análise de sentimentos**: Adicionar pós-processamento das transcrições
4. **Interface web**: Criar Flask/FastAPI opcional

## 🚀 Vantagens da Versão Otimizada

### ✅ Simplificações
- **Sem Redis**: Controle direto no MongoDB
- **Sem Celery**: ThreadPoolExecutor nativo
- **Menos dependências**: Instalação mais rápida
- **Configuração simples**: Apenas .env

### ✅ Performance
- **GPU otimizada**: Batch processing para RTX 4070
- **Paralelização**: Workers nativos Python
- **Cache inteligente**: Reutilização de modelos
- **Monitoramento**: Métricas em tempo real

### ✅ Escalabilidade
- **Processamento contínuo**: Auto-queue automático
- **Recuperação de erros**: Retry automático
- **Limpeza inteligente**: Reset de conversas falhadas
- **API REST**: Integração fácil

### ✅ Arquitetura Simplificada

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WhatsApp      │───▶│  MongoDB        │───▶│  Auto Queue     │
│   Data Import   │    │  (Raw Data)     │    │  (ThreadPool)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐           │
│   Audio         │◄───│  Parallel       │◄──────────┘
│   Downloader    │    │  Workers        │
└─────────────────┘    └─────────────────┘
                                │
┌─────────────────┐    ┌─────────────────┐
│   Whisper       │◄───│  Batch          │
│   (RTX 4070)    │    │  Processor      │
└─────────────────┘    └─────────────────┘
                                │
┌─────────────────┐    ┌─────────────────┐
│   Ollama        │◄───│  Conversation   │
│   (Llama 3.1)   │    │  Analyzer       │
└─────────────────┘    └─────────────────┘
                                │
┌─────────────────┐    ┌─────────────────┐
│   MongoDB       │◄───│  Results        │
│   (Processed)   │    │  Storage        │
└─────────────────┘    └─────────────────┘
```

## 📝 Changelog

### v2.0 - Versão Refatorada (Atual)
- ✅ **Services organizados** (DRY, KISS, Single Responsibility)
- ✅ **CLI refatorado** com comandos mais intuitivos
- ✅ **Testes completos** para todos os componentes
- ✅ **Documentação detalhada** com exemplos reais
- ✅ **Integração Laravel** documentada
- ✅ **Estrutura de dados** explicada
- ✅ **Troubleshooting** abrangente
- ✅ Removido Docker e complexidade desnecessária
- ✅ Scripts Python diretos e simples
- ✅ Organização de arquivos por ID
- ✅ Processamento modular separado
- ✅ Instalação automatizada
- ✅ Campo `audio_transcriptions` para controle
- ✅ **Removido Redis/Celery** - controle direto no MongoDB
- ✅ **ThreadPoolExecutor** para paralelização nativa
- ✅ **Otimizado para RTX 4070** com batch processing
- ✅ **Sistema de monitoramento** com métricas em tempo real
- ✅ **API REST completa** com documentação automática
- ✅ **Processamento automático** contínuo
- ✅ **Análise de conversas** com Ollama/Llama 3.1

### v1.0 - Versão Original
- Sistema básico de transcrição
- Integração MongoDB simples
- Sistema baseado em containers
- API web FastAPI
- Integração Ollama para análise LLM

## 🤝 Contribuição

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para detalhes.

---

**Desenvolvido para processamento eficiente de áudios WhatsApp Business** 🎙️⚡

**Integrado com sistema Laravel existente** 🔗📊