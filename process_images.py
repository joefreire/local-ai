#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processador para análise e descrição de imagens
"""
import sys
import os
import time
from pathlib import Path
from datetime import datetime
import argparse

# Configurar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

def process_single_image(image_path: str, prompt: str = None, save_json: bool = True):
    """Processar uma única imagem"""
    print("🖼️ Processador de Imagem - Análise Individual")
    print("=" * 60)
    
    try:
        from src.services.image_service import ImageService
        
        # Inicializar serviço
        print("🔧 Inicializando serviço de imagens...")
        image_service = ImageService()
        
        # Verificar se arquivo existe
        if not Path(image_path).exists():
            print(f"❌ Arquivo não encontrado: {image_path}")
            return False
        
        # Prompt padrão se não fornecido
        if not prompt:
            prompt = "Esta é uma captura de tela. Descreva o conteúdo visível em português."
        
        print(f"📁 Analisando: {Path(image_path).name}")
        print(f"💬 Prompt: {prompt}")
        print("-" * 50)
        
        # Analisar imagem
        print("🔍 Iniciando análise...")
        start_time = time.time()
        
        result = image_service.analyze_image(image_path, prompt)
        
        elapsed_time = time.time() - start_time
        
        if not result:
            print("❌ Falha na análise da imagem")
            return False
        
        # Mostrar resultado
        print("✅ Análise concluída!")
        print(f"⏱️ Tempo: {elapsed_time:.1f}s")
        print(f"📊 Tamanho da imagem: {result['image_size']}")
        print(f"🔧 Dispositivo: {result['device']}")
        print(f"🤖 Modelo: {result['model']}")
        print("\n📝 Descrição:")
        print("-" * 50)
        print(result['description'])
        print("-" * 50)
        
        # Salvar JSON se solicitado
        if save_json:
            print("\n💾 Salvando resultado...")
            json_path = f"image_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            import json
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Resultado salvo: {json_path}")
        
        # Limpeza
        image_service.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

def process_image_batch(image_dir: str, prompt: str = None, limit: int = None):
    """Processar múltiplas imagens em lote"""
    print("🖼️ Processador de Imagem - Análise em Lote")
    print("=" * 60)
    
    try:
        from src.services.image_service import ImageService
        
        # Inicializar serviço
        print("🔧 Inicializando serviço de imagens...")
        image_service = ImageService()
        
        # Buscar imagens
        image_dir_path = Path(image_dir)
        if not image_dir_path.exists():
            print(f"❌ Diretório não encontrado: {image_dir}")
            return False
        
        # Extensões suportadas
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        
        # Encontrar imagens
        image_files = []
        for ext in image_extensions:
            image_files.extend(image_dir_path.glob(f"*{ext}"))
            image_files.extend(image_dir_path.glob(f"*{ext.upper()}"))
        
        if not image_files:
            print("❌ Nenhuma imagem encontrada no diretório")
            return False
        
        # Aplicar limite se especificado
        if limit:
            image_files = image_files[:limit]
        
        print(f"📁 Encontradas {len(image_files)} imagens")
        
        # Prompt padrão se não fornecido
        if not prompt:
            prompt = "Esta é uma captura de tela. Descreva o conteúdo visível em português."
        
        print(f"💬 Prompt: {prompt}")
        print("-" * 50)
        
        # Processar imagens
        total_processed = 0
        total_successful = 0
        total_failed = 0
        start_time = time.time()
        
        for i, image_path in enumerate(image_files, 1):
            print(f"\n📷 [{i}/{len(image_files)}] Processando: {image_path.name}")
            
            try:
                # Analisar imagem
                result = image_service.analyze_image(str(image_path), prompt)
                
                if result:
                    # Mostrar preview
                    description_preview = result['description'][:100] + "..." if len(result['description']) > 100 else result['description']
                    print(f"   ✅ Sucesso - {result['generation_time']:.1f}s")
                    print(f"   📝 Preview: {description_preview}")
                    
                    # Salvar resultado
                    json_path = f"image_analysis_{image_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    
                    import json
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    
                    print(f"   💾 Salvo: {json_path}")
                    total_successful += 1
                else:
                    print(f"   ❌ Falha na análise")
                    total_failed += 1
                
                total_processed += 1
                
            except Exception as e:
                print(f"   ❌ Erro: {e}")
                total_failed += 1
                total_processed += 1
        
        # Resumo final
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("🎉 PROCESSAMENTO CONCLUÍDO!")
        print("=" * 60)
        print(f"⏱️ Tempo total: {elapsed_time:.1f}s")
        print(f"📊 Imagens processadas: {total_processed}")
        print(f"✅ Sucessos: {total_successful}")
        print(f"❌ Falhas: {total_failed}")
        print(f"📈 Taxa de sucesso: {(total_successful/total_processed*100):.1f}%" if total_processed > 0 else "N/A")
        
        # Limpeza
        image_service.close()
        
        return total_failed == 0
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_image_service():
    """Testar serviço de imagens"""
    print("🧪 Teste do Serviço de Imagens")
    print("=" * 60)
    
    try:
        from src.services.image_service import ImageService
        
        # Inicializar serviço
        print("🔧 Inicializando serviço...")
        image_service = ImageService()
        
        # Testar GPU
        gpu_info = image_service.get_gpu_info()
        print(f"🔧 Dispositivo: {gpu_info['device_name']}")
        print(f"💾 Memória: {gpu_info.get('total_memory', 0) / (1024**3):.1f}GB" if gpu_info.get('total_memory') else "N/A")
        
        print("✅ Serviço inicializado com sucesso!")
        
        # Limpeza
        image_service.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Processar e analisar imagens")
    parser.add_argument("--image", type=str, help="Caminho para uma única imagem")
    parser.add_argument("--dir", type=str, help="Diretório com imagens para processar em lote")
    parser.add_argument("--prompt", type=str, help="Prompt personalizado para análise")
    parser.add_argument("--limit", type=int, help="Limite de imagens para processar em lote")
    parser.add_argument("--no-save", action="store_true", help="Não salvar resultado em JSON")
    parser.add_argument("--test", action="store_true", help="Apenas testar o serviço")
    
    args = parser.parse_args()
    
    if args.test:
        success = test_image_service()
    elif args.image:
        success = process_single_image(
            args.image, 
            args.prompt, 
            save_json=not args.no_save
        )
    elif args.dir:
        success = process_image_batch(
            args.dir, 
            args.prompt, 
            args.limit
        )
    else:
        print("❌ Especifique --image, --dir ou --test")
        print("💡 Use --help para ver todas as opções")
        return 1
    
    if success:
        print("\n✅ Processamento concluído com sucesso!")
        return 0
    else:
        print("\n❌ Processamento concluído com erros")
        return 1

if __name__ == "__main__":
    sys.exit(main())
