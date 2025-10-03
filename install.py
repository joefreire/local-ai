#!/usr/bin/env python3
"""
Script de instalação e validação do ambiente local
Verifica e instala todas as dependências necessárias
"""

import sys
import subprocess
import pkg_resources
import os
from pathlib import Path
import platform

def print_header(title):
    """Imprimir cabeçalho formatado"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_python_version():
    """Verificar versão do Python"""
    print("🐍 Verificando versão do Python...")
    
    version = sys.version_info
    required_major, required_minor = 3, 8
    
    if version.major < required_major or (version.major == required_major and version.minor < required_minor):
        print(f"❌ Python {required_major}.{required_minor}+ é necessário. Versão atual: {version.major}.{version.minor}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} OK")
    return True

def check_ffmpeg():
    """Verificar se FFmpeg está instalado"""
    print("\n🎵 Verificando FFmpeg...")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Extrair versão do FFmpeg
            version_line = result.stdout.split('\n')[0]
            print(f"✅ {version_line}")
            return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    print("❌ FFmpeg não encontrado")
    print_ffmpeg_install_instructions()
    return False

def print_ffmpeg_install_instructions():
    """Instruções para instalar FFmpeg"""
    system = platform.system().lower()
    
    print("\n📖 Como instalar FFmpeg:")
    
    if system == "windows":
        print("   Windows:")
        print("   1. Baixe em: https://ffmpeg.org/download.html")
        print("   2. Extraia e adicione à variável PATH")
        print("   3. OU use chocolatey: choco install ffmpeg")
        print("   4. OU use winget: winget install FFmpeg")
    
    elif system == "darwin":  # macOS
        print("   macOS:")
        print("   brew install ffmpeg")
    
    else:  # Linux
        print("   Linux (Ubuntu/Debian):")
        print("   sudo apt update && sudo apt install ffmpeg")
        print("   Linux (CentOS/RHEL):")
        print("   sudo yum install ffmpeg")

def read_requirements():
    """Ler arquivo requirements.txt"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"❌ Arquivo {requirements_file} não encontrado")
        return []
    
    with open(requirements_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    packages = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            packages.append(line)
    
    return packages

def check_package_installed(package_name):
    """Verificar se um pacote está instalado"""
    try:
        # Remover especificadores de versão
        clean_name = package_name.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
        pkg_resources.get_distribution(clean_name)
        return True
    except pkg_resources.DistributionNotFound:
        return False

def install_package(package):
    """Instalar um pacote via pip"""
    try:
        print(f"📦 Instalando {package}...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {package} instalado com sucesso")
            return True
        else:
            print(f"❌ Erro ao instalar {package}:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout ao instalar {package}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado ao instalar {package}: {e}")
        return False

def check_and_install_packages():
    """Verificar e instalar pacotes Python"""
    print("\n📦 Verificando dependências Python...")
    
    packages = read_requirements()
    if not packages:
        print("❌ Nenhuma dependência encontrada no requirements.txt")
        return False
    
    missing_packages = []
    installed_packages = []
    
    # Verificar quais estão instalados
    for package in packages:
        if check_package_installed(package):
            installed_packages.append(package)
        else:
            missing_packages.append(package)
    
    # Relatório
    if installed_packages:
        print(f"\n✅ Já instalados ({len(installed_packages)}):")
        for pkg in installed_packages:
            print(f"   • {pkg}")
    
    if missing_packages:
        print(f"\n📥 Para instalar ({len(missing_packages)}):")
        for pkg in missing_packages:
            print(f"   • {pkg}")
        
        # Perguntar se deve instalar
        response = input(f"\n❓ Instalar {len(missing_packages)} pacotes faltantes? (s/N): ").lower()
        
        if response in ['s', 'sim', 'y', 'yes']:
            failed_installs = []
            
            for package in missing_packages:
                if not install_package(package):
                    failed_installs.append(package)
            
            if failed_installs:
                print(f"\n❌ Falha ao instalar {len(failed_installs)} pacotes:")
                for pkg in failed_installs:
                    print(f"   • {pkg}")
                return False
            else:
                print(f"\n🎉 Todos os {len(missing_packages)} pacotes instalados com sucesso!")
        else:
            print("\n⏸️ Instalação cancelada pelo usuário")
            return False
    
    return True

def create_directories():
    """Criar diretórios necessários"""
    print("\n📁 Criando estrutura de diretórios...")
    
    dirs = [
        "downloads",
        "logs",
        "temp"
    ]
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✅ {dir_name}/ já existe")
        else:
            dir_path.mkdir(exist_ok=True)
            print(f"📁 {dir_name}/ criado")

def check_env_file():
    """Verificar arquivo .env"""
    print("\n🔐 Verificando configurações...")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✅ Arquivo .env encontrado")
        
        # Verificar se tem as variáveis essenciais
        with open(env_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        required_vars = ['MONGODB_URL', 'MONGODB_DATABASE']
        missing_vars = []
        
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️ Variáveis faltantes no .env: {', '.join(missing_vars)}")
        else:
            print("✅ Variáveis essenciais configuradas")
    
    else:
        print("❌ Arquivo .env não encontrado")
        if env_example.exists():
            print("💡 Copie .env.example para .env e configure suas variáveis")
        else:
            print("💡 Crie um arquivo .env com suas configurações MongoDB")

def main():
    """Função principal"""
    print_header("INSTALADOR DE AMBIENTE LOCAL")
    print("🎙️ Transcritor de Áudio - Configuração Local")
    
    success = True
    
    # 1. Verificar Python
    if not check_python_version():
        success = False
    
    # 2. Verificar FFmpeg
    if not check_ffmpeg():
        success = False
    
    # 3. Verificar e instalar dependências Python
    if success and not check_and_install_packages():
        success = False
    
    # 4. Criar diretórios
    if success:
        create_directories()
    
    # 5. Verificar .env
    if success:
        check_env_file()
    
    # Resultado final
    print_header("RESULTADO")
    
    if success:
        print("🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n📋 Próximos passos:")
        print("   1. Configure o arquivo .env com suas credenciais MongoDB")
        print("   2. Execute: python check_pending.py")
        print("   3. Execute: python ultra_transcribe.py")
    else:
        print("❌ INSTALAÇÃO INCOMPLETA")
        print("\n🔧 Resolva os problemas acima e execute novamente")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)