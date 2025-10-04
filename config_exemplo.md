# 📋 Configurações do Sistema - Guia Completo

## 🔧 Arquivo .env

### Configurações Obrigatórias

```bash
# === MONGODB ===
# URL de conexão (Atlas ou local)
MONGODB_URL=mongodb+srv://usuario:senha@cluster.mongodb.net/
MONGODB_DATABASE=dashboard_whatsapp

# === WHISPER ===
# Modelo Whisper (recomendado: large-v3)
WHISPER_MODEL=large-v3
WHISPER_LANGUAGE=pt
```

### Configurações de GPU

```bash
# === GPU SETTINGS ===
# Para RTX 4070 (8.6GB VRAM)
GPU_BATCH_SIZE=4
GPU_MEMORY_FRACTION=0.8

# Para RTX 3060 (6GB VRAM)
# GPU_BATCH_SIZE=2
# GPU_MEMORY_FRACTION=0.7

# Para RTX 4090 (24GB VRAM)
# GPU_BATCH_SIZE=8
# GPU_MEMORY_FRACTION=0.9
```

### Configurações de Processamento

```bash
# === PROCESSAMENTO ===
# Workers paralelos (recomendado: 8)
MAX_CONCURRENT_JOBS=8

# Timeout para download (segundos)
AUDIO_DOWNLOAD_TIMEOUT=60

# Intervalo de processamento automático (segundos)
PROCESSING_INTERVAL=30
```

### Configurações de Análise (Opcional)

```bash
# === OLLAMA ===
# URL do servidor Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Modelo LLM
OLLAMA_MODEL=llama3.1:8b

# Para análise mais rápida
# OLLAMA_MODEL=llama3.1:3b

# Para análise mais precisa
# OLLAMA_MODEL=llama3.1:70b
```

## 🎯 Configurações por Cenário

### Cenário 1: Desenvolvimento/Teste

```bash
# Configuração leve para desenvolvimento
WHISPER_MODEL=base
GPU_BATCH_SIZE=1
GPU_MEMORY_FRACTION=0.5
MAX_CONCURRENT_JOBS=2
LOG_LEVEL=DEBUG
```

### Cenário 2: Produção (RTX 4070)

```bash
# Configuração otimizada para RTX 4070
WHISPER_MODEL=large-v3
GPU_BATCH_SIZE=4
GPU_MEMORY_FRACTION=0.8
MAX_CONCURRENT_JOBS=8
LOG_LEVEL=INFO
```

### Cenário 3: Alta Performance (RTX 4090)

```bash
# Configuração para máxima performance
WHISPER_MODEL=large-v3
GPU_BATCH_SIZE=8
GPU_MEMORY_FRACTION=0.9
MAX_CONCURRENT_JOBS=16
LOG_LEVEL=INFO
```

### Cenário 4: CPU Only

```bash
# Configuração sem GPU
WHISPER_MODEL=base
GPU_BATCH_SIZE=1
GPU_MEMORY_FRACTION=0.0
MAX_CONCURRENT_JOBS=4
LOG_LEVEL=INFO
```

## 📊 Modelos Whisper

| Modelo | Tamanho | VRAM | Velocidade | Qualidade |
|--------|---------|------|------------|-----------|
| `tiny` | 39 MB | 1 GB | Muito rápido | Baixa |
| `base` | 74 MB | 1 GB | Rápido | Boa |
| `small` | 244 MB | 2 GB | Médio | Boa |
| `medium` | 769 MB | 5 GB | Lento | Muito boa |
| `large` | 1550 MB | 10 GB | Muito lento | Excelente |
| `large-v3` | 1550 MB | 10 GB | Muito lento | **Excelente** |

**Recomendação**: `large-v3` para RTX 4070

## 🧠 Modelos Ollama

| Modelo | Tamanho | RAM | Velocidade | Qualidade |
|--------|---------|-----|------------|-----------|
| `llama3.1:3b` | 2 GB | 4 GB | Rápido | Boa |
| `llama3.1:8b` | 4.7 GB | 8 GB | Médio | **Muito boa** |
| `llama3.1:70b` | 40 GB | 80 GB | Lento | Excelente |

**Recomendação**: `llama3.1:8b` para análise equilibrada

## 🔍 Verificação de Configuração

### Teste de Configuração

```powershell
# Testar configuração atual
python cli_refactored.py test-all

# Verificar GPU especificamente
python cli_refactored.py test-gpu

# Verificar MongoDB
python cli_refactored.py test-mongodb
```

### Comandos de Verificação

```powershell
# Verificar CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

# Verificar Whisper
python -c "import whisper; print('Whisper OK')"

# Verificar Ollama
curl http://localhost:11434/api/tags
```

## ⚠️ Troubleshooting de Configuração

### Problema: GPU não detectada

**Solução:**
```bash
# Verificar CUDA
nvidia-smi

# Reinstalar PyTorch com CUDA
pip uninstall torch torchaudio
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Problema: Memória GPU insuficiente

**Solução:**
```bash
# Reduzir batch size
GPU_BATCH_SIZE=2

# Reduzir uso de memória
GPU_MEMORY_FRACTION=0.6

# Usar modelo menor
WHISPER_MODEL=base
```

### Problema: MongoDB não conecta

**Solução:**
```bash
# Verificar URL
echo $MONGODB_URL

# Testar conexão
python -c "import pymongo; client = pymongo.MongoClient('$MONGODB_URL'); print('OK' if client.admin.command('ping') else 'ERRO')"
```

### Problema: Ollama não responde

**Solução:**
```bash
# Verificar se está rodando
curl http://localhost:11434/api/tags

# Iniciar Ollama
ollama serve

# Baixar modelo
ollama pull llama3.1:8b
```

## 📈 Otimizações de Performance

### Para RTX 4070

```bash
# Configuração otimizada
WHISPER_MODEL=large-v3
GPU_BATCH_SIZE=4
GPU_MEMORY_FRACTION=0.8
MAX_CONCURRENT_JOBS=8
```

**Resultado esperado:**
- 50-100 áudios/minuto
- 3000-6000 áudios/hora
- <2min por áudio

### Para RTX 3060

```bash
# Configuração conservadora
WHISPER_MODEL=medium
GPU_BATCH_SIZE=2
GPU_MEMORY_FRACTION=0.7
MAX_CONCURRENT_JOBS=6
```

**Resultado esperado:**
- 30-60 áudios/minuto
- 1800-3600 áudios/hora
- <3min por áudio

### Para CPU Only

```bash
# Configuração CPU
WHISPER_MODEL=base
GPU_BATCH_SIZE=1
GPU_MEMORY_FRACTION=0.0
MAX_CONCURRENT_JOBS=4
```

**Resultado esperado:**
- 5-15 áudios/minuto
- 300-900 áudios/hora
- 5-10min por áudio

## 🔄 Configurações Dinâmicas

### Ajustar durante execução

```python
# No código Python
from src.config import Config

# Ajustar batch size dinamicamente
Config.GPU_BATCH_SIZE = 2

# Ajustar workers
Config.MAX_CONCURRENT_JOBS = 4
```

### Monitoramento de recursos

```powershell
# Monitorar GPU
nvidia-smi -l 1

# Monitorar CPU/RAM
htop

# Monitorar logs
tail -f logs/processing.log
```

## 📝 Logs e Debugging

### Níveis de Log

```bash
# Debug completo
LOG_LEVEL=DEBUG

# Informações normais
LOG_LEVEL=INFO

# Apenas erros
LOG_LEVEL=ERROR
```

### Localização dos Logs

```
logs/
├── processing.log      # Logs de processamento
├── audio.log          # Logs de transcrição
├── analysis.log       # Logs de análise
└── system.log         # Logs do sistema
```

### Comandos de Debug

```powershell
# Ver logs em tempo real
tail -f logs/processing.log

# Filtrar erros
grep "ERROR" logs/*.log

# Ver últimas 100 linhas
tail -100 logs/processing.log
```
