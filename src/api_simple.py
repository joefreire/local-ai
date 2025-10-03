"""
API FastAPI simplificada - sem Redis, apenas MongoDB
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from .queue_manager_simple import SimpleQueueManager
from .monitoring import SystemMonitor
from .database import DatabaseManager
from .config import Config

# Configurar logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Criar aplicação FastAPI
app = FastAPI(
    title="WhatsApp Audio Transcription System - Simplified",
    description="Sistema simplificado de transcrição e análise de áudios do WhatsApp (sem Redis)",
    version="2.0.0-simple",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instâncias globais
queue_manager = SimpleQueueManager()
monitor = SystemMonitor()
db = DatabaseManager()

@app.on_event("startup")
async def startup_event():
    """Evento de inicialização"""
    logger.info("🚀 Iniciando API Simplificada do Sistema de Transcrição")
    
    # Iniciar monitoramento
    monitor.start_monitoring(interval=60)
    
    # Iniciar processamento automático
    queue_manager.start_processing(interval=30)
    
    logger.info("✅ API Simplificada iniciada com sucesso")

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de finalização"""
    logger.info("🛑 Finalizando API Simplificada")
    
    # Parar processamento
    queue_manager.stop_processing()
    
    # Parar monitoramento
    monitor.stop_monitoring()
    
    # Fechar conexões
    queue_manager.close()
    monitor.close()
    db.close()
    
    logger.info("✅ API Simplificada finalizada")

# ==================== ENDPOINTS DE STATUS ====================

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "WhatsApp Audio Transcription System - Simplified",
        "version": "2.0.0-simple",
        "status": "online",
        "architecture": "MongoDB-only (no Redis)",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Verificação de saúde do sistema"""
    try:
        # Testar componentes
        db_status = "ok"
        try:
            db.get_conversations_with_pending_audios(1)
        except Exception:
            db_status = "error"
        
        processing_status = "ok"
        try:
            queue_manager.get_processing_status()
        except Exception:
            processing_status = "error"
        
        return {
            "status": "healthy" if all([db_status == "ok", processing_status == "ok"]) else "unhealthy",
            "components": {
                "database": db_status,
                "processing": processing_status,
                "monitoring": "active" if monitor.monitoring_active else "inactive"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

# ==================== ENDPOINTS DE PROCESSAMENTO ====================

@app.get("/processing/status")
async def get_processing_status():
    """Obter status do processamento"""
    try:
        status = queue_manager.get_processing_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/processing/start")
async def start_processing(interval: int = Query(default=30, ge=10, le=300)):
    """Iniciar processamento automático"""
    try:
        queue_manager.start_processing(interval)
        return {
            "message": f"Processamento automático iniciado (intervalo: {interval}s)",
            "interval": interval,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/processing/stop")
async def stop_processing():
    """Parar processamento automático"""
    try:
        queue_manager.stop_processing()
        return {
            "message": "Processamento automático parado",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/processing/cleanup-failed")
async def cleanup_failed_conversations(max_age_hours: int = Query(default=24, ge=1, le=168)):
    """Limpar conversas com erro antigas"""
    try:
        result = queue_manager.cleanup_failed_conversations(max_age_hours)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ENDPOINTS DE CONVERSAS ====================

@app.get("/conversations/pending")
async def get_pending_conversations(
    limit: int = Query(default=50, ge=1, le=1000)
):
    """Obter conversas com áudios pendentes"""
    try:
        conversations = queue_manager.discover_pending_conversations(limit)
        return {
            "conversations": conversations,
            "count": len(conversations),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversations/{conversation_id}/process")
async def process_conversation(conversation_id: str):
    """Processar uma conversa específica"""
    try:
        result = queue_manager.process_single_conversation(conversation_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversations/batch/process")
async def process_multiple_conversations(
    conversation_ids: List[str],
    background_tasks: BackgroundTasks = None
):
    """Processar múltiplas conversas"""
    try:
        if len(conversation_ids) > 50:
            raise HTTPException(status_code=400, detail="Máximo 50 conversas por lote")
        
        results = queue_manager.process_multiple_conversations(conversation_ids)
        
        successful = len([r for r in results if r.get('status') not in ['error']])
        failed = len(results) - successful
        
        return {
            "message": f"Processamento concluído: {successful} sucessos, {failed} falhas",
            "total_conversations": len(conversation_ids),
            "successful": successful,
            "failed": failed,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{conversation_id}/audios")
async def get_conversation_audios(conversation_id: str):
    """Obter áudios pendentes de uma conversa"""
    try:
        audio_urls = db.get_pending_audios_for_conversation(conversation_id)
        return {
            "conversation_id": conversation_id,
            "pending_audios": audio_urls,
            "count": len(audio_urls),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{conversation_id}/analysis")
async def get_conversation_analysis(conversation_id: str):
    """Obter análise de uma conversa"""
    try:
        conversation_data = db.get_conversation_text_for_analysis(conversation_id)
        if not conversation_data:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
        return {
            "conversation_id": conversation_id,
            "analysis_data": conversation_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ENDPOINTS DE MÉTRICAS ====================

@app.get("/metrics")
async def get_metrics():
    """Obter métricas do sistema"""
    try:
        metrics = monitor.collect_system_metrics()
        return {
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/summary")
async def get_metrics_summary():
    """Obter resumo das métricas"""
    try:
        summary = monitor.get_metrics_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/gpu")
async def get_gpu_metrics():
    """Obter métricas da GPU"""
    try:
        gpu_status = queue_manager.get_gpu_status()
        return gpu_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts")
async def get_alerts():
    """Obter alertas do sistema"""
    try:
        alerts = monitor.get_alerts()
        return {
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ENDPOINTS DE CONTROLE ====================

@app.post("/control/monitoring/start")
async def start_monitoring(interval: int = Query(default=60, ge=10, le=300)):
    """Iniciar monitoramento"""
    try:
        monitor.start_monitoring(interval)
        return {
            "message": f"Monitoramento iniciado (intervalo: {interval}s)",
            "interval": interval,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/control/monitoring/stop")
async def stop_monitoring():
    """Parar monitoramento"""
    try:
        monitor.stop_monitoring()
        return {
            "message": "Monitoramento parado",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ENDPOINTS DE ESTATÍSTICAS ====================

@app.get("/stats/overview")
async def get_stats_overview():
    """Obter visão geral das estatísticas"""
    try:
        # Status do processamento
        processing_status = queue_manager.get_processing_status()
        
        # Métricas do sistema
        metrics = monitor.collect_system_metrics()
        
        # Estatísticas de performance
        performance = monitor.get_performance_stats()
        
        # Alertas
        alerts = monitor.get_alerts()
        
        return {
            "system": {
                "cpu_percent": metrics['system']['cpu_percent'],
                "memory_percent": metrics['system']['memory_percent'],
                "disk_percent": metrics['system']['disk_usage_percent'],
                "uptime_hours": metrics['system']['uptime_seconds'] / 3600
            },
            "processing": {
                "active": processing_status.get('processing_active', False),
                "max_workers": processing_status.get('max_workers', 0),
                "pending_conversations": processing_status.get('total_conversations', 0),
                "pending_audios": processing_status.get('total_audios_pending', 0),
                "transcribed_audios": processing_status.get('total_audios_transcribed', 0),
                "progress_percent": processing_status.get('transcription_progress', 0)
            },
            "performance": {
                "throughput_per_hour": performance.get('throughput_audios_per_hour', 0),
                "efficiency_score": performance.get('efficiency_score', 0)
            },
            "alerts": {
                "count": len(alerts),
                "critical": len([a for a in alerts if a['type'] == 'critical']),
                "warnings": len([a for a in alerts if a['type'] == 'warning'])
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ENDPOINTS DE INFORMAÇÕES ====================

@app.get("/info/configuration")
async def get_configuration():
    """Obter configurações do sistema"""
    try:
        return {
            "architecture": "MongoDB-only (simplified)",
            "mongodb": {
                "database": Config.MONGODB_DATABASE,
                "uri": Config.MONGODB_URI.replace(Config.MONGODB_URI.split('@')[0].split('//')[1], "***") if '@' in Config.MONGODB_URI else Config.MONGODB_URI
            },
            "whisper": {
                "model": Config.WHISPER_MODEL,
                "language": Config.WHISPER_LANGUAGE,
                "gpu_batch_size": Config.GPU_BATCH_SIZE
            },
            "ollama": {
                "base_url": Config.OLLAMA_BASE_URL,
                "model": Config.OLLAMA_MODEL
            },
            "processing": {
                "max_concurrent_jobs": Config.MAX_CONCURRENT_JOBS,
                "audio_download_timeout": Config.AUDIO_DOWNLOAD_TIMEOUT
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=Config.LOG_LEVEL.lower()
    )
