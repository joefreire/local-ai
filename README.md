# 🎙️ Transcritor de Áudio Local

Sistema simples e eficiente para transcrição de áudios de diários do WhatsApp usando **OpenAI Whisper**, **MongoDB** e **Python**. 

**Abordagem Local**: Sem Docker, sem APIs web complexas - apenas scripts Python diretos e organizados.

## ✨ Características

- 🎵 **Whisper Local**: Transcrição de alta qualidade em português
- 📂 **Organização**: Arquivos por diário e mensagem
- 🔄 **Processamento Modular**: Download → Transcrição → Sincronização
- 💾 **MongoDB**: Integração com diários existentes do Laravel
- 🚀 **Instalação Simples**: Script automatizado para ambiente local
- 📊 **Rastreamento**: Campo `audio_transcriptions` para controle

## 📁 Estrutura do Projeto

```
transcrever_audio/
├── check_pending.py      # Verificar diários pendentes
├── ultra_transcribe.py   # Transcritor principal
├── install.py           # Instalação automatizada
├── requirements.txt     # Dependências Python
├── .env                 # Configurações (crie a partir do .env.example)
├── downloads/           # Arquivos organizados por ID
│   ├── {diario_id}/
│   │   ├── {message_id}.oga
│   │   ├── {message_id}_transcription.json
│   │   └── ...
├── logs/                # Logs do sistema
└── temp/                # Arquivos temporários
```

## 🚀 Instalação

### 1. Pré-requisitos
- **Python 3.8+**
- **FFmpeg** (para processamento de áudio)
- **MongoDB Atlas** ou local

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

### 3. Configuração Manual

Se preferir instalar manualmente:

```powershell
# Instalar dependências
pip install -r requirements.txt

# Criar diretórios
mkdir downloads, logs, temp

# Configurar ambiente
copy .env.example .env
# Editar .env com suas configurações
```

## ⚙️ Configuração

### Arquivo .env

```bash
# MongoDB (Atlas ou local)
MONGODB_URL=mongodb+srv://usuario:senha@cluster.mongodb.net/
MONGODB_DATABASE=dashboard_whatsapp

# Opcionais
WHISPER_MODEL=turbo  # tiny, base, small, medium, large, turbo
```

### FFmpeg

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

## 🎯 Uso

### 1. Verificar Diários Pendentes

```powershell
# Listar diários com áudios pendentes
python check_pending.py

# Atualizar campo audio_transcriptions
python check_pending.py --update-transcriptions

# Criar diário de teste
python check_pending.py --create-test
```

### 2. Processamento Completo

```powershell
# Processar tudo: baixar + transcrever + salvar
python ultra_transcribe.py --limit 5
```

### 3. Processamento Modular

```powershell
# 1. Apenas baixar áudios (sem transcrever)
python ultra_transcribe.py --download-only --limit 10

# 2. Apenas transcrever áudios já baixados
python ultra_transcribe.py --transcribe-only

# 3. Sincronizar transcrições com MongoDB
python ultra_transcribe.py --sync-db
```

## 📊 Fluxo de Trabalho

### Abordagem Modular Recomendada

```mermaid
graph TD
    A[Verificar Pendentes] --> B[Download de Áudios]
    B --> C[Transcrição Local]
    C --> D[Sincronização MongoDB]
    
    A --> E[check_pending.py]
    B --> F[ultra_transcribe.py --download-only]
    C --> G[ultra_transcribe.py --transcribe-only]
    D --> H[ultra_transcribe.py --sync-db]
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
  "file_path": "/path/to/audio.oga",
  "transcribed_at": "2025-10-03T14:30:00"
}
```

## 🔍 Comandos Úteis

### Verificação de Status

```powershell
# Ver estatísticas detalhadas
python check_pending.py --limit 100

# Ver arquivos baixados
ls downloads/

# Ver logs
Get-Content logs/*.log | Select-Object -Last 50
```

### Limpeza

```powershell
# Limpar arquivos temporários
Remove-Item temp/* -Recurse -Force

# Limpar downloads específicos
Remove-Item downloads/{diario_id} -Recurse -Force
```

## 🛠️ Estrutura do MongoDB

### Campo `audio_transcriptions`

```javascript
{
  "_id": ObjectId("..."),
  "user_name": "João Silva",
  "date_formatted": "03/10/2025",
  "status_audios": "completed",
  
  // Novo campo de controle
  "audio_transcriptions": {
    "total_audios": 5,
    "transcribed_audios": 5,
    "pending_audios": 0,
    "transcription_status": "completed",
    "last_updated": "2025-10-03T14:30:00"
  },
  
  "contacts": [
    {
      "messages": [
        {
          "_id": "3A6E7CBC0A08D764BA55",
          "media_type": "audio",
          "media_url": "1759445969529.oga",
          "direct_media_url": "https://api.../1759445969529.oga",
          
          // Campo de transcrição
          "audio_transcription": "Texto transcrito...",
          "transcription_data": { /* objeto completo */ },
          "transcription_status": "completed"
        }
      ]
    }
  ]
}
```

## ⚡ Performance e Otimizações

### Modelo Whisper

- **tiny**: Mais rápido, menor qualidade
- **base**: Equilibrado para testes
- **small**: Boa qualidade, velocidade razoável
- **medium**: Alta qualidade, mais lento
- **large**: Máxima qualidade, muito lento
- **turbo**: **Recomendado** - qualidade alta, velocidade otimizada

### Configuração no .env

```bash
WHISPER_MODEL=turbo  # Padrão recomendado
```

### Processamento em Lotes

```powershell
# Processar muitos diários em pequenos lotes
python ultra_transcribe.py --limit 5   # Lote pequeno
python ultra_transcribe.py --limit 10  # Lote médio
python ultra_transcribe.py --limit 20  # Lote grande
```

## 🐛 Troubleshooting

### Problemas Comuns

**1. FFmpeg não encontrado**
```powershell
# Verificar instalação
ffmpeg -version

# Instalar se necessário
choco install ffmpeg
```

**2. Erro de conexão MongoDB**
```powershell
# Testar conexão
python check_pending.py

# Verificar .env
cat .env
```

**3. Erro na transcrição**
```powershell
# Verificar áudio baixado
ls downloads/{diario_id}/

# Tentar transcrição isolada
python ultra_transcribe.py --transcribe-only
```

**4. Memória insuficiente**
```bash
# Usar modelo menor
WHISPER_MODEL=small
```

## 📈 Monitoramento

### Logs

```powershell
# Ver logs em tempo real
Get-Content logs/*.log -Wait

# Ver últimos erros
Select-String "ERROR" logs/*.log | Select-Object -Last 10
```

### Estatísticas

```powershell
# Total de arquivos baixados
Get-ChildItem downloads/ -Recurse -File | Measure-Object

# Total de transcrições
Get-ChildItem downloads/ -Recurse -Filter "*_transcription.json" | Measure-Object
```

## 🔧 Desenvolvimento

### Estrutura do Código

- `check_pending.py`: Verificação e controle de diários
- `ultra_transcribe.py`: Processamento principal de transcrição
- `install.py`: Instalação e verificação do ambiente

### Extensões

Para adicionar novas funcionalidades:

1. **Novos formatos de áudio**: Modificar `extract_audio_urls()`
2. **Outros provedores de transcrição**: Criar nova classe transcriber
3. **Análise de sentimentos**: Adicionar pós-processamento das transcrições
4. **Interface web**: Criar Flask/FastAPI opcional

## 📝 Changelog

### v2.0 - Abordagem Local
- ✅ Removido Docker e complexidade desnecessária
- ✅ Scripts Python diretos e simples
- ✅ Organização de arquivos por ID
- ✅ Processamento modular separado
- ✅ Instalação automatizada
- ✅ Campo `audio_transcriptions` para controle

### v1.0 - Versão Docker
- Sistema baseado em containers
- API web FastAPI
- Integração Ollama para análise LLM

## 🤝 Contribuição

1. Fork o projeto
2. Crie sua feature branch
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para detalhes.

---

**Desenvolvido para transcrição eficiente de áudios do WhatsApp Business** 🎙️📱