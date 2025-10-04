# Configuração do Ollama para Análise de Conversas

## 1. Instalação do Ollama

### Windows
```bash
# Baixar e instalar do site oficial
# https://ollama.ai/download/windows
```

### Linux/Mac
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

## 2. Iniciar o Serviço

```bash
# Iniciar o servidor Ollama
ollama serve
```

O servidor ficará rodando em: `http://localhost:11434`

## 3. Baixar Modelos

### Modelo Recomendado (Llama 3.2)
```bash
ollama pull llama3.2
```

### Outros Modelos Disponíveis
```bash
# Modelos menores (mais rápidos)
ollama pull llama3.2:1b
ollama pull llama3.2:3b

# Modelos maiores (mais precisos)
ollama pull llama3.2:70b
ollama pull llama3.2:90b

# Modelos especializados
ollama pull codellama
ollama pull mistral
```

## 4. Testar Instalação

### Teste Rápido
```bash
python test_ollama_rapido.py
```

### Teste Completo
```bash
python test_ollama_isolado.py
```

### Teste com Modelo Específico
```bash
python test_ollama_isolado.py llama3.2:1b
```

## 5. Configuração no Sistema

### Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Configuração no config.py
```python
class Config:
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')
```

## 6. Comandos Úteis

```bash
# Listar modelos instalados
ollama list

# Remover modelo
ollama rm modelo_nome

# Ver informações do modelo
ollama show llama3.2

# Executar modelo interativamente
ollama run llama3.2
```

## 7. Solução de Problemas

### Erro de Conexão
- Verifique se o Ollama está rodando: `ollama serve`
- Teste a URL: `curl http://localhost:11434/api/tags`

### Modelo Não Encontrado
- Baixe o modelo: `ollama pull modelo_nome`
- Verifique modelos disponíveis: `ollama list`

### Erro de Memória
- Use modelo menor: `ollama pull llama3.2:1b`
- Feche outros programas
- Verifique RAM disponível

### Performance Lenta
- Use GPU se disponível
- Configure CUDA para PyTorch
- Use modelos menores para testes

## 8. Exemplos de Uso

### Análise de Conversa
```python
from src.services.analysis_service import LlamaService

service = LlamaService()
result = service.analyze_conversation(conversation_data)
```

### Teste Manual
```python
import requests

payload = {
    "model": "llama3.2",
    "prompt": "Analise esta conversa: 'Oi, tudo bem?'",
    "stream": False
}

response = requests.post(
    "http://localhost:11434/api/generate",
    json=payload
)

print(response.json()['response'])
```

## 9. Modelos Recomendados por Uso

### Para Desenvolvimento/Testes
- `llama3.2:1b` - Muito rápido, menos preciso
- `llama3.2:3b` - Equilíbrio entre velocidade e precisão

### Para Produção
- `llama3.2` (8b) - Boa precisão, velocidade moderada
- `llama3.2:70b` - Máxima precisão, requer mais recursos

### Para Análise de Código
- `codellama` - Especializado em código
- `codellama:7b` - Versão menor do CodeLlama
