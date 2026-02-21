import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Client, Operation
from services.remnawave import remnawave_service
from services.audit import audit_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def deactivate_expired_clients():
    """Деактивация просроченных клиентов"""
    db = SessionLocal()
    try:
        # Находим всех просроченных активных клиентов
        expired_clients = db.query(Client).filter(
            Client.status == "active",
            Client.expires_at < datetime.now(timezone.utc)
        ).all()
        
        for client in expired_clients:
            logger.info(f"Deactivating expired client: {client.id}")
            
            # Блокируем в RemnaWave
            result = await remnawave_service.block_client(client.id)
            
            if result["success"]:
                # Обновляем статус в базе
                client.status = "blocked"
                db.commit()
                
                # Логируем операцию
                audit_service.log_operation(
                    db=db,
                    client_id=client.id,
                    action="auto_deactivate",
                    result="success"
                )
                
                logger.info(f"Successfully deactivated client: {client.id}")
            else:
                # Логируем ошибку
                audit_service.log_operation(
                    db=db,
                    client_id=client.id,
                    action="auto_deactivate",
                    result="fail",
                    error=result.get("error", "Unknown error")
                )
                
                logger.error(f"Failed to deactivate client {client.id}: {result.get('error')}")
    
    except Exception as e:
        logger.error(f"Error in deactivate_expired_clients: {str(e)}")
    finally:
        db.close()


async def scheduler_task():
    """Основная задача планировщика"""
    while True:
        try:
            await deactivate_expired_clients()
            # Проверяем каждые 5 минут
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")
            await asyncio.sleep(60)  # При ошибке ждем 1 минуту


def start_scheduler():
    """Запуск планировщика в фоновом режиме"""
    asyncio.create_task(scheduler_task())
    logger.info("Scheduler started")
