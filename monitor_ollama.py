#!/usr/bin/env python3
"""
Monitor de Performance do Ollama/Llama
Mostra estatísticas em tempo real: tokens, velocidade, requests, etc.
"""

import requests
import time
import json
import psutil
from datetime import datetime
import os
import sys

class OllamaMonitor:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_time": 0,
            "requests_per_minute": 0,
            "tokens_per_second": 0,
            "start_time": time.time()
        }
        
    def get_ollama_status(self):
        """Obter status do Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/ps", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            return {"error": str(e)}
        return None
    
    def get_system_stats(self):
        """Obter estatísticas do sistema"""
        try:
            # CPU e Memória
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Processos do Ollama
            ollama_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if 'ollama' in proc.info['name'].lower():
                        ollama_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "ollama_processes": ollama_processes
            }
        except Exception as e:
            return {"error": str(e)}
    
    def format_time(self, seconds):
        """Formatar tempo em formato legível"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def clear_screen(self):
        """Limpar tela"""
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
        except:
            print("\n" * 50)  # Fallback para Windows
    
    def display_stats(self):
        """Exibir estatísticas"""
        self.clear_screen()
        
        print("🔍 MONITOR OLLAMA/LLAMA - ESTATÍSTICAS EM TEMPO REAL")
        print("=" * 60)
        
        # Status do Ollama
        ollama_status = self.get_ollama_status()
        if ollama_status and "error" not in ollama_status:
            models = ollama_status.get("models", [])
            if models:
                model = models[0]
                print(f"🤖 Modelo Ativo: {model.get('name', 'N/A')}")
                print(f"📊 Tamanho: {model.get('size', 0) / (1024**3):.1f} GB")
                print(f"🧠 Contexto: {model.get('details', {}).get('context_length', 'N/A')} tokens")
                print(f"⏰ Expira em: {model.get('expires_at', 'N/A')}")
            else:
                print("❌ Nenhum modelo carregado")
        else:
            print("❌ Ollama não está respondendo")
        
        print("\n" + "=" * 60)
        
        # Estatísticas do Sistema
        sys_stats = self.get_system_stats()
        if "error" not in sys_stats:
            print(f"💻 CPU: {sys_stats.get('cpu_percent', 0):.1f}%")
            print(f"🧠 Memória: {sys_stats.get('memory_percent', 0):.1f}% ({sys_stats.get('memory_available_gb', 0):.1f} GB livres)")
            
            ollama_procs = sys_stats.get('ollama_processes', [])
            if ollama_procs:
                print(f"🔄 Processos Ollama: {len(ollama_procs)}")
                for proc in ollama_procs:
                    print(f"   PID {proc['pid']}: CPU {proc['cpu_percent']:.1f}%, Mem {proc['memory_percent']:.1f}%")
        
        print("\n" + "=" * 60)
        
        # Estatísticas de Uso
        uptime = time.time() - self.stats["start_time"]
        print(f"⏱️  Uptime: {self.format_time(uptime)}")
        print(f"📈 Requests: {self.stats['total_requests']}")
        print(f"🎯 Tokens: {self.stats['total_tokens']}")
        
        if self.stats['total_time'] > 0:
            print(f"⚡ Velocidade: {self.stats['total_tokens'] / self.stats['total_time']:.2f} tokens/s")
        
        if uptime > 0:
            print(f"📊 Requests/min: {self.stats['total_requests'] / (uptime / 60):.2f}")
        
        print("\n" + "=" * 60)
        print("💡 Dicas:")
        print("   - Pressione Ctrl+C para sair")
        print("   - Execute uma análise para ver estatísticas em tempo real")
        print("   - Monitore CPU/Memória para otimização")
        print("=" * 60)
    
    def run(self):
        """Executar monitor"""
        print("🚀 Iniciando monitor Ollama...")
        print("📊 Aguardando atividade...")
        
        try:
            while True:
                self.display_stats()
                time.sleep(2)  # Atualizar a cada 2 segundos
        except KeyboardInterrupt:
            print("\n\n👋 Monitor finalizado!")
        except Exception as e:
            print(f"\n❌ Erro no monitor: {e}")

def main():
    """Função principal"""
    print("🔍 Monitor de Performance Ollama/Llama")
    print("=" * 40)
    
    # Verificar se Ollama está rodando
    try:
        response = requests.get("http://localhost:11434/api/ps", timeout=5)
        if response.status_code != 200:
            print("❌ Ollama não está rodando ou não está acessível")
            print("💡 Execute: ollama serve")
            return
    except Exception as e:
        print(f"❌ Erro ao conectar com Ollama: {e}")
        print("💡 Verifique se o Ollama está rodando: ollama serve")
        return
    
    print("✅ Ollama detectado!")
    print("🚀 Iniciando monitor...")
    
    monitor = OllamaMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
