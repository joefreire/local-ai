#!/usr/bin/env python3
"""
Script para instalar suporte GPU (PyTorch com CUDA)
"""
import subprocess
import sys
import torch

def check_gpu_availability():
    """Verificar se GPU está disponível"""
    print("🔍 Verificando disponibilidade de GPU...")
    
    # Verificar se nvidia-smi está disponível
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ NVIDIA GPU detectada")
            return True
        else:
            print("❌ NVIDIA GPU não encontrada")
            return False
    except FileNotFoundError:
        print("❌ nvidia-smi não encontrado - GPU NVIDIA não disponível")
        return False

def check_pytorch_cuda():
    """Verificar se PyTorch tem suporte CUDA"""
    print("🔍 Verificando suporte CUDA no PyTorch...")
    
    try:
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"GPU count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
            return True
        else:
            print("❌ PyTorch não tem suporte CUDA")
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar PyTorch: {e}")
        return False

def install_pytorch_cuda():
    """Instalar PyTorch com suporte CUDA"""
    print("📦 Instalando PyTorch com suporte CUDA...")
    
    try:
        # Desinstalar versão CPU
        print("🗑️ Removendo PyTorch CPU...")
        subprocess.run([sys.executable, '-m', 'pip', 'uninstall', 'torch', 'torchaudio', '-y'], 
                      check=True)
        
        # Instalar versão CUDA
        print("⬇️ Instalando PyTorch CUDA...")
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', 'torch', 'torchaudio',
            '--index-url', 'https://download.pytorch.org/whl/cu121'
        ], check=True)
        
        print("✅ PyTorch CUDA instalado com sucesso!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro na instalação: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Instalador de Suporte GPU para PyTorch")
    print("=" * 50)
    
    # Verificar GPU
    if not check_gpu_availability():
        print("\n⚠️ GPU NVIDIA não detectada")
        print("💡 O sistema continuará funcionando com CPU")
        print("💡 Para usar GPU, instale drivers NVIDIA e execute este script novamente")
        return
    
    # Verificar PyTorch atual
    if check_pytorch_cuda():
        print("\n✅ PyTorch já tem suporte CUDA - nada a fazer!")
        return
    
    # Instalar PyTorch CUDA
    print("\n📦 Instalando suporte GPU...")
    if install_pytorch_cuda():
        print("\n🎉 Instalação concluída!")
        print("🔄 Reinicie o sistema para aplicar as mudanças")
        
        # Verificar novamente
        print("\n🔍 Verificando instalação...")
        if check_pytorch_cuda():
            print("✅ Suporte GPU ativado com sucesso!")
        else:
            print("❌ Problema na instalação - usando CPU")
    else:
        print("\n❌ Falha na instalação - sistema continuará com CPU")

if __name__ == "__main__":
    main()

