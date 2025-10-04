#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador para suporte a análise de imagens
"""
import sys
import subprocess
import platform
from pathlib import Path

def install_image_dependencies():
    """Instalar dependências para análise de imagens"""
    print("🖼️ Instalador de Suporte para Análise de Imagens")
    print("=" * 60)
    
    # Dependências básicas
    basic_deps = [
        "transformers>=4.40.0",
        "torchvision",
        "pillow",
        "accelerate"
    ]
    
    # Dependências para GPU (se disponível)
    gpu_deps = [
        "torch",
        "torchaudio"
    ]
    
    print("📦 Instalando dependências básicas...")
    for dep in basic_deps:
        try:
            print(f"   📥 Instalando {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"   ✅ {dep} instalado")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Erro ao instalar {dep}: {e}")
            return False
    
    print("\n🔧 Verificando suporte a GPU...")
    try:
        import torch
        if torch.cuda.is_available():
            print("   🚀 GPU detectada! Instalando dependências otimizadas...")
            
            # Instalar PyTorch com suporte CUDA
            cuda_version = torch.version.cuda
            print(f"   📊 CUDA detectada: {cuda_version}")
            
            # Instalar versão otimizada para GPU
            gpu_pytorch = f"torch torchaudio --index-url https://download.pytorch.org/whl/cu{cuda_version.replace('.', '')}"
            
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + gpu_pytorch.split())
                print("   ✅ PyTorch GPU otimizado instalado")
            except subprocess.CalledProcessError:
                print("   ⚠️ Falha ao instalar versão GPU, usando versão padrão")
                for dep in gpu_deps:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
        else:
            print("   💻 GPU não disponível, instalando versão CPU...")
            for dep in gpu_deps:
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                
    except ImportError:
        print("   ⚠️ PyTorch não encontrado, instalando versão padrão...")
        for dep in gpu_deps:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
    
    print("\n🧪 Testando instalação...")
    try:
        # Testar imports
        import torch
        import torchvision
        import transformers
        from PIL import Image
        import accelerate
        
        print("   ✅ Todas as dependências importadas com sucesso")
        
        # Testar GPU
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name()
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"   🚀 GPU: {gpu_name} ({gpu_memory:.1f}GB)")
        else:
            print("   💻 Usando CPU")
        
        # Testar modelo
        print("   📥 Testando carregamento do modelo LLaVA...")
        from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
        
        model_name = "llava-hf/llava-v1.6-mistral-7b-hf"
        processor = LlavaNextProcessor.from_pretrained(model_name)
        print("   ✅ Modelo LLaVA carregado com sucesso")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no teste: {e}")
        return False

def create_test_image():
    """Criar imagem de teste"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import os
        
        # Criar imagem de teste
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        # Desenhar elementos simples
        draw.rectangle([50, 50, 350, 250], outline='black', width=2)
        draw.ellipse([100, 100, 200, 200], fill='red')
        draw.text((150, 220), "Teste", fill='black')
        
        # Salvar imagem
        test_path = Path("test_image.png")
        img.save(test_path)
        
        print(f"   🖼️ Imagem de teste criada: {test_path}")
        return str(test_path)
        
    except Exception as e:
        print(f"   ❌ Erro ao criar imagem de teste: {e}")
        return None

def main():
    """Função principal"""
    print("🚀 Iniciando instalação de suporte para análise de imagens...")
    print(f"🖥️ Sistema: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {sys.version}")
    print()
    
    # Instalar dependências
    success = install_image_dependencies()
    
    if success:
        print("\n🎉 Instalação concluída com sucesso!")
        print("\n💡 Próximos passos:")
        print("   1. Teste o serviço: python process_images.py --test")
        print("   2. Analise uma imagem: python process_images.py --image caminho/para/imagem.jpg")
        print("   3. Processe um diretório: python process_images.py --dir caminho/para/diretorio")
        
        # Criar imagem de teste
        test_image = create_test_image()
        if test_image:
            print(f"\n🧪 Para testar, execute:")
            print(f"   python process_images.py --image {test_image}")
        
        return 0
    else:
        print("\n❌ Instalação falhou")
        print("💡 Verifique os erros acima e tente novamente")
        return 1

if __name__ == "__main__":
    sys.exit(main())
