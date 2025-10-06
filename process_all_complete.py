#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Master - Executa todos os três processadores principais em ordem
1. process_all_audios.py - Processa áudios pendentes
2. process_all_images.py - Processa imagens pendentes  
3. process_all_analyses.py - Analisa conversas
"""
import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

# Configurar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

def run_command(command, description, timeout=3600):
    """Executa um comando e retorna o resultado"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"⏰ Iniciado em: {datetime.now().strftime('%H:%M:%S')}")
    print(f"💻 Comando: {' '.join(command)}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Executar comando
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8'
        )
        
        elapsed_time = time.time() - start_time
        
        # Mostrar saída
        if result.stdout:
            print("📤 SAÍDA:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️  ERROS/AVISOS:")
            print(result.stderr)
        
        # Resultado
        if result.returncode == 0:
            print(f"\n✅ {description} - CONCLUÍDO COM SUCESSO")
            print(f"⏱️  Tempo: {elapsed_time:.1f}s")
            return True
        else:
            print(f"\n❌ {description} - FALHOU")
            print(f"⏱️  Tempo: {elapsed_time:.1f}s")
            print(f"🔢 Código de saída: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        print(f"\n⏰ {description} - TIMEOUT ({timeout}s)")
        print(f"⏱️  Tempo decorrido: {elapsed_time:.1f}s")
        return False
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n💥 {description} - ERRO: {e}")
        print(f"⏱️  Tempo decorrido: {elapsed_time:.1f}s")
        return False

def process_all_complete(limit=None, dry_run=False, force=False, contact_filter=None, skip_audios=False, skip_images=False, skip_analyses=False):
    """Executa todos os três processadores em ordem"""
    
    print("🎯 PROCESSADOR COMPLETO - TODOS OS MÓDULOS")
    print("=" * 60)
    print("📋 Ordem de execução:")
    print("   1️⃣  Áudios pendentes (process_all_audios.py)")
    print("   2️⃣  Imagens pendentes (process_all_images.py)")
    print("   3️⃣  Análises v2 (process_all_analyses.py) - Por contato + resumo global")
    print("=" * 60)
    
    if dry_run:
        print("🧪 MODO DRY-RUN ativado - apenas listando pendências")
    
    if force:
        print("⚡ MODO FORCE ativado - reprocessando TUDO")
    
    if limit:
        print(f"📊 Limite de conversas: {limit}")
    
    if contact_filter:
        print(f"🎯 Filtro de contato: {contact_filter}")
    
    if skip_audios:
        print("⏭️  Pulando processamento de áudios")
    
    if skip_images:
        print("⏭️  Pulando processamento de imagens")
    
    if skip_analyses:
        print("⏭️  Pulando análises de conversas")
    
    print()
    
    # Estatísticas gerais
    total_start_time = time.time()
    results = {
        'audios': {'success': False, 'time': 0},
        'images': {'success': False, 'time': 0},
        'analyses': {'success': False, 'time': 0}
    }
    
    # 1. PROCESSAR ÁUDIOS
    if not skip_audios:
        audio_start = time.time()
        audio_command = [sys.executable, "process_all_audios.py"]
        
        if limit:
            audio_command.extend(["--limit", str(limit)])
        if dry_run:
            audio_command.append("--dry-run")
        if force:
            audio_command.append("--force")
        
        results['audios']['success'] = run_command(
            audio_command,
            "PROCESSAMENTO DE ÁUDIOS PENDENTES",
            timeout=7200  # 2 horas
        )
        results['audios']['time'] = time.time() - audio_start
        
        if not results['audios']['success'] and not dry_run:
            print("\n⚠️  Áudios falharam - continuando com imagens...")
    else:
        print("\n⏭️  Pulando processamento de áudios")
        results['audios']['success'] = True  # Considerar como sucesso para continuar
    
    # 2. PROCESSAR IMAGENS
    if not skip_images:
        image_start = time.time()
        image_command = [sys.executable, "process_all_images.py"]
        
        if limit:
            image_command.extend(["--limit", str(limit)])
        if dry_run:
            image_command.append("--dry-run")
        if force:
            image_command.append("--force")
        
        results['images']['success'] = run_command(
            image_command,
            "PROCESSAMENTO DE IMAGENS PENDENTES",
            timeout=7200  # 2 horas
        )
        results['images']['time'] = time.time() - image_start
        
        if not results['images']['success'] and not dry_run:
            print("\n⚠️  Imagens falharam - continuando com análises...")
    else:
        print("\n⏭️  Pulando processamento de imagens")
        results['images']['success'] = True  # Considerar como sucesso para continuar
    
    # 3. PROCESSAR ANÁLISES (V2)
    if not skip_analyses:
        analysis_start = time.time()
        analysis_command = [sys.executable, "process_all_analyses.py"]
        
        if limit:
            analysis_command.extend(["--limit", str(limit)])
        if dry_run:
            analysis_command.append("--dry-run")
        if force:
            analysis_command.append("--force")
        if contact_filter:
            analysis_command.extend(["--contact", contact_filter])
        
        results['analyses']['success'] = run_command(
            analysis_command,
            "ANÁLISE DE CONVERSAS V2 (Por Contato + Resumo Global)",
            timeout=10800  # 3 horas
        )
        results['analyses']['time'] = time.time() - analysis_start
    else:
        print("\n⏭️  Pulando análises de conversas")
        results['analyses']['success'] = True  # Considerar como sucesso para continuar
    
    # RESUMO FINAL
    total_elapsed = time.time() - total_start_time
    
    print("\n" + "="*80)
    print("🎉 PROCESSAMENTO COMPLETO FINALIZADO!")
    print("="*80)
    print(f"⏱️  Tempo total: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print()
    
    print("📊 RESULTADOS POR MÓDULO:")
    print("-" * 50)
    
    # Áudios
    status_audios = "✅ SUCESSO" if results['audios']['success'] else "❌ FALHOU"
    print(f"🎵 Áudios:     {status_audios:<12} ({results['audios']['time']:.1f}s)")
    
    # Imagens
    status_images = "✅ SUCESSO" if results['images']['success'] else "❌ FALHOU"
    print(f"🖼️  Imagens:   {status_images:<12} ({results['images']['time']:.1f}s)")
    
    # Análises
    status_analyses = "✅ SUCESSO" if results['analyses']['success'] else "❌ FALHOU"
    print(f"🧠 Análises:   {status_analyses:<12} ({results['analyses']['time']:.1f}s)")
    
    print("-" * 50)
    
    # Status geral
    all_success = all(result['success'] for result in results.values())
    if all_success:
        print("🎉 TODOS OS MÓDULOS EXECUTADOS COM SUCESSO!")
        return True
    else:
        failed_modules = [name for name, result in results.items() if not result['success']]
        print(f"⚠️  MÓDULOS COM FALHA: {', '.join(failed_modules)}")
        return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description="Script Master - Executa todos os processadores em ordem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Processar tudo (modo normal)
  python process_all_complete.py

  # Apenas listar pendências (dry-run)
  python process_all_complete.py --dry-run

  # Processar com limite
  python process_all_complete.py --limit 10

  # Reprocessar tudo (force)
  python process_all_complete.py --force

  # Pular áudios e imagens, apenas análises
  python process_all_complete.py --skip-audios --skip-images

  # Análise apenas de um contato específico
  python process_all_complete.py --contact "MARIA SILVA"

  # Processar tudo com limite e force
  python process_all_complete.py --limit 5 --force
        """
    )
    
    parser.add_argument("--limit", type=int, help="Limite de conversas para processar")
    parser.add_argument("--dry-run", action="store_true", help="Apenas listar pendências, não processar")
    parser.add_argument("--force", action="store_true", help="Reprocessar TUDO, ignorando status anterior")
    parser.add_argument("--contact", type=str, help="Filtrar análises por nome de contato específico")
    parser.add_argument("--skip-audios", action="store_true", help="Pular processamento de áudios")
    parser.add_argument("--skip-images", action="store_true", help="Pular processamento de imagens")
    parser.add_argument("--skip-analyses", action="store_true", help="Pular análises de conversas")
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.skip_audios and args.skip_images and args.skip_analyses:
        print("❌ Erro: Não é possível pular todos os módulos!")
        print("💡 Pelo menos um módulo deve ser executado.")
        return 1
    
    if args.contact and not args.skip_analyses:
        print(f"🎯 Filtro de contato aplicado: {args.contact}")
        print("💡 O filtro se aplica apenas às análises de conversas")
    
    # Executar processamento
    success = process_all_complete(
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force,
        contact_filter=args.contact,
        skip_audios=args.skip_audios,
        skip_images=args.skip_images,
        skip_analyses=args.skip_analyses
    )
    
    if success:
        print("\n✅ Processamento completo finalizado com sucesso!")
        return 0
    else:
        print("\n⚠️  Processamento completo finalizado com algumas falhas")
        return 1

if __name__ == "__main__":
    sys.exit(main())


