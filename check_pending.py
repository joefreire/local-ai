#!/usr/bin/env python3
"""
Comando simples para verificar diários pendentes de transcrição no MongoDB
Busca itens que NÃO têm status_audios = 'done' e TÊM mensagens de áudio
"""

import os
import sys
from datetime import datetime
import pymongo
from bson import ObjectId
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

# Configurações MongoDB do .env
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "dashboard_whatsapp")

def connect_mongo():
    """Conectar no MongoDB"""
    try:
        client = pymongo.MongoClient(MONGODB_URL)
        db = client[MONGODB_DATABASE]
        
        # Testar conexão
        client.admin.command('ping')
        
        print(f"✅ Conectado no MongoDB: {MONGODB_DATABASE}")
        return db
        
    except Exception as e:
        print(f"❌ Erro ao conectar no MongoDB: {e}")
        return None

def count_audio_messages(contacts):
    """Contar mensagens de áudio nos contatos"""
    total_audios = 0
    transcribed_audios = 0
    
    if not contacts or not isinstance(contacts, list):
        return {'total': 0, 'transcribed': 0}
    
    for contact in contacts:
        messages = contact.get('messages', [])
        for message in messages:
            # Verificar se é áudio baseado no exemplo fornecido
            is_audio = (
                message.get('media_type') == 'audio' or
                message.get('is_audio', False) or
                message.get('type') == 'audio' or
                message.get('message_type') == 'audio' or
                'audio' in str(message.get('file_path', '')).lower() or
                str(message.get('media_url', '')).endswith(('.mp3', '.wav', '.ogg', '.m4a', '.oga')) or
                str(message.get('direct_media_url', '')).endswith(('.mp3', '.wav', '.ogg', '.m4a', '.oga'))
            )
            
            if is_audio:
                total_audios += 1
                # Verificar se já tem transcrição
                if message.get('audio_transcription'):
                    transcribed_audios += 1
    
    return {'total': total_audios, 'transcribed': transcribed_audios}

def find_pending_diarios(db, limit=50):
    """Buscar diários que precisam de transcrição"""
    
    # Query: NÃO tem status_audios = 'completed' E TEM mensagens de áudio
    query = {
        "$and": [
            {
                "$or": [
                    {"status_audios": {"$ne": "completed"}},
                    {"status_audios": {"$exists": False}}
                ]
            },
            {
                "$or": [
                    {"audio_messages": {"$gt": 0}},
                    {"media_messages": {"$gt": 0}}
                ]
            }
        ]
    }
    
    print(f"🔍 Buscando diários pendentes...")
    print(f"📋 Query: status_audios ≠ 'completed' E (audio_messages > 0 OU media_messages > 0)")
    
    cursor = db.diarios.find(query).limit(limit)
    diarios = list(cursor)
    
    print(f"📊 Encontrados: {len(diarios)} diários")
    
    return diarios

def analyze_diario(diario):
    """Analisar um diário e contar áudios"""
    diario_id = str(diario.get('_id', 'N/A'))
    user_name = diario.get('user_name', 'Desconhecido')
    status_audios = diario.get('status_audios', 'N/A')
    audio_messages = diario.get('audio_messages', 0)
    media_messages = diario.get('media_messages', 0)
    
    # Contar áudios reais nos contatos
    contacts = diario.get('contacts', [])
    audio_stats = count_audio_messages(contacts)
    
    # Calcular status de transcrição
    transcription_status = "N/A"
    if audio_stats['total'] > 0:
        if audio_stats['transcribed'] == 0:
            transcription_status = "⏸️ Nenhum"
        elif audio_stats['transcribed'] == audio_stats['total']:
            transcription_status = "✅ Completo"
        else:
            transcription_status = f"⚠️ {audio_stats['transcribed']}/{audio_stats['total']}"
    
    return {
        'id': diario_id[:8],  # Primeiros 8 chars
        'user_name': user_name,
        'status_audios': status_audios,
        'audio_messages': audio_messages,
        'media_messages': media_messages,
        'real_audio_count': audio_stats['total'],
        'transcribed_count': audio_stats['transcribed'],
        'transcription_status': transcription_status,
        'date': diario.get('date_formatted', 'N/A')
    }

def update_audio_transcriptions_field(db, diario_id):
    """Atualizar campo audio_transcriptions com base nas transcrições existentes"""
    try:
        # Buscar o diário
        diario = db.diarios.find_one({"_id": ObjectId(diario_id)})
        if not diario:
            return False
            
        audio_stats = count_audio_messages(diario.get('contacts', []))
        
        # Criar estrutura do campo audio_transcriptions
        audio_transcriptions = {
            'total_audios': audio_stats['total'],
            'transcribed_audios': audio_stats['transcribed'], 
            'pending_audios': audio_stats['total'] - audio_stats['transcribed'],
            'transcription_status': 'completed' if audio_stats['transcribed'] == audio_stats['total'] and audio_stats['total'] > 0 else 'pending',
            'last_updated': datetime.now()
        }
        
        # Atualizar no MongoDB
        result = db.diarios.update_one(
            {"_id": ObjectId(diario_id)},
            {
                "$set": {
                    "audio_transcriptions": audio_transcriptions,
                    "updated_at": datetime.now()
                }
            }
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        print(f"❌ Erro ao atualizar audio_transcriptions: {e}")
        return False

def create_test_diario(db):
    """Criar um diário de teste para demonstração"""
    test_diario = {
        "user_name": "TESTE TRANSCRIÇÃO",
        "date_formatted": "03/10/2025",
        "audio_messages": 2,
        "media_messages": 1,
        "status_audios": "pending",  # Status pendente
        "contacts": [
            {
                "contact_name": "João Teste",
                "messages": [
                    {
                        "_id": "msg_001",
                        "media_type": "audio",
                        "is_audio": True,
                        "media_url": "audio1.mp3",
                        "direct_media_url": "https://example.com/audio1.mp3",
                        "created_at": "10:30",
                        "audio_transcription": None  # Sem transcrição ainda
                    },
                    {
                        "_id": "msg_002", 
                        "media_type": "audio",
                        "is_audio": True,
                        "media_url": "audio2.oga",
                        "direct_media_url": "https://example.com/audio2.oga",
                        "created_at": "10:35",
                        "audio_transcription": "Exemplo de transcrição já feita"  # Com transcrição
                    }
                ]
            }
        ],
        "audio_transcriptions": {
            "total_audios": 2,
            "transcribed_audios": 1,
            "pending_audios": 1,
            "transcription_status": "pending",
            "last_updated": datetime.now()
        },
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    result = db.diarios.insert_one(test_diario)
    print(f"✅ Diário de teste criado: {result.inserted_id}")
    return result.inserted_id

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verificador de diários pendentes")
    parser.add_argument("--create-test", action="store_true", help="Criar um diário de teste")
    parser.add_argument("--update-transcriptions", action="store_true", help="Atualizar campo audio_transcriptions em todos os diários")
    parser.add_argument("--limit", type=int, default=50, help="Limite de diários para buscar")
    
    args = parser.parse_args()
    
    print("🎙️ Verificador de Diários Pendentes")
    print("=" * 50)
    print(f"🔗 MongoDB: {MONGODB_URL}")
    print(f"📂 Database: {MONGODB_DATABASE}")
    print()
    
    # Conectar
    db = connect_mongo()
    if db is None:
        return 1
    
    try:
        # Criar diário de teste se solicitado
        if args.create_test:
            print("🧪 Criando diário de teste...")
            create_test_diario(db)
            print()
        
        # Atualizar campo audio_transcriptions se solicitado
        if args.update_transcriptions:
            print("🔄 Atualizando campo audio_transcriptions em todos os diários...")
            cursor = db.diarios.find({})
            updated_count = 0
            total_count = 0
            
            for diario in cursor:
                total_count += 1
                if update_audio_transcriptions_field(db, str(diario['_id'])):
                    updated_count += 1
                    
            print(f"✅ Campo audio_transcriptions atualizado em {updated_count}/{total_count} diários")
            print()
        
        # Buscar diários pendentes
        diarios = find_pending_diarios(db, limit=args.limit)
        
        if not diarios:
            print("📭 Nenhum diário pendente encontrado!")
            print("💡 Todos os diários já foram processados ou não têm áudios.")
            return 0
        
        print(f"\n📋 DIÁRIOS PENDENTES DE TRANSCRIÇÃO:")
        print("-" * 95)
        print(f"{'ID':<10} {'USUÁRIO':<20} {'STATUS':<12} {'ÁUDIOS':<8} {'TRANSCRIÇÕES':<15} {'DATA'}")
        print("-" * 95)
        
        total_audios_pendentes = 0
        total_transcribed = 0
        
        for diario in diarios:
            info = analyze_diario(diario)
            
            print(f"{info['id']:<10} {info['user_name'][:19]:<20} {info['status_audios']:<12} {info['real_audio_count']:<8} {info['transcription_status']:<15} {info['date']}")
            
            total_audios_pendentes += info['real_audio_count']
            total_transcribed += info['transcribed_count']
        
        print("-" * 95)
        print(f"📊 RESUMO:")
        print(f"   📋 Total de diários pendentes: {len(diarios)}")
        print(f"   🎵 Total de áudios encontrados: {total_audios_pendentes}")
        print(f"   ✅ Áudios já transcritos: {total_transcribed}")
        print(f"   ⏸️ Áudios restantes para transcrever: {total_audios_pendentes - total_transcribed}")
        print(f"   📅 Data da verificação: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)