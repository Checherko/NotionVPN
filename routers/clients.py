from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid

from database import get_db
from models import Client
from schemas import ClientCreate, ClientResponse, ClientExtend, ClientConfig, ErrorResponse
from services.remnawave import remnawave_service
from services.audit import audit_service

router = APIRouter()


@router.post("/", response_model=dict)
async def create_client(client_data: ClientCreate, db: Session = Depends(get_db)):
    """Создание нового клиента"""
    
    # Проверка на идемпотентность - можно добавить проверку по ID операции
    client_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=client_data.days)
    
    try:
        # Создаем клиента в базе данных
        client = Client(
            id=client_id,
            status="active",
            expires_at=expires_at
        )
        
        db.add(client)
        db.commit()
        db.refresh(client)
        
        # Создаем клиента в RemnaWave
        remna_result = await remnawave_service.create_client(client_id)
        
        if not remna_result["success"]:
            # Откатываем изменения в базе если RemnaWave не ответил
            db.delete(client)
            db.commit()
            
            # Логируем ошибку
            audit_service.log_operation(
                db=db,
                client_id=client_id,
                action="create",
                payload={"days": client_data.days},
                result="fail",
                error=remna_result.get("error")
            )
            
            raise HTTPException(
                status_code=500,
                detail={"error": "Failed to create client in RemnaWave", "message": remna_result.get("error")}
            )
        
        # Логируем успешную операцию
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="create",
            payload={"days": client_data.days},
            result="success"
        )
        
        return {"id": client_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="create",
            payload={"days": client_data.days},
            result="fail",
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/", response_model=List[ClientResponse])
def get_clients(
    status: Optional[str] = Query(None, description="Фильтр по статусу: active, blocked"),
    expired: Optional[bool] = Query(None, description="Фильтр по истечению срока"),
    db: Session = Depends(get_db)
):
    """Получение списка клиентов с фильтрами"""
    
    query = db.query(Client)
    
    if status:
        if status not in ["active", "blocked"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid status", "message": "Status must be 'active' or 'blocked'"}
            )
        query = query.filter(Client.status == status)
    
    if expired is not None:
        now = datetime.now(timezone.utc)
        if expired:
            query = query.filter(Client.expires_at < now)
        else:
            query = query.filter(Client.expires_at >= now)
    
    clients = query.order_by(Client.created_at.desc()).all()
    return clients


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """Получение информации о клиенте"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail={"error": "Client not found", "message": f"Client with id {client_id} not found"}
        )
    
    return client


@router.delete("/{client_id}")
async def delete_client(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Удаление/деактивация клиента
    - Если клиент активен - сначала блокируется в RemnaWave, затем удаляется из базы
    - Если клиент уже заблокирован - просто удаляется из базы
    """
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail={"error": "Client not found", "message": f"Client with id {client_id} not found"}
        )
    
    try:
        # Если клиент активен, сначала блокируем его в RemnaWave
        if client.status == "active":
            remna_result = await remnawave_service.block_client(client_id)
            
            if not remna_result["success"]:
                audit_service.log_operation(
                    db=db,
                    client_id=client_id,
                    action="delete",
                    result="fail",
                    error=remna_result.get("error")
                )
                
                raise HTTPException(
                    status_code=500,
                    detail={"error": "Failed to block client in RemnaWave", "message": remna_result.get("error")}
                )
        
        # Удаляем клиента из RemnaWave
        remna_delete_result = await remnawave_service.delete_client(client_id)
        
        # Логируем операцию удаления
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="delete",
            result="success" if remna_delete_result["success"] else "fail",
            error=remna_delete_result.get("error") if not remna_delete_result["success"] else None
        )
        
        # Удаляем связанные операции вручную
        from models import Operation
        db.query(Operation).filter(Operation.client_id == client_id).delete()
        
        # Удаляем клиента из базы данных
        db.delete(client)
        db.commit()
        
        return {"message": "Client deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="delete",
            result="fail",
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/{client_id}/extend")
async def extend_client(
    client_id: uuid.UUID, 
    extend_data: ClientExtend, 
    db: Session = Depends(get_db)
):
    """Продление подписки клиента"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail={"error": "Client not found", "message": f"Client with id {client_id} not found"}
        )
    
    try:
        # Обновляем срок действия
        if client.expires_at < datetime.now(timezone.utc):
            # Если срок истек, считаем от текущей даты
            client.expires_at = datetime.now(timezone.utc) + timedelta(days=extend_data.days)
        else:
            # Если срок не истек, продляем от текущей даты окончания
            client.expires_at = client.expires_at + timedelta(days=extend_data.days)
        
        db.commit()
        db.refresh(client)
        
        # Логируем операцию
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="extend",
            payload={"days": extend_data.days},
            result="success"
        )
        
        return {"message": "Subscription extended successfully", "expires_at": client.expires_at}
        
    except Exception as e:
        db.rollback()
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="extend",
            payload={"days": extend_data.days},
            result="fail",
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/{client_id}/block")
async def block_client(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """Блокировка клиента"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail={"error": "Client not found", "message": f"Client with id {client_id} not found"}
        )
    
    if client.status == "blocked":
        return {"message": "Client is already blocked"}
    
    try:
        # Блокируем в RemnaWave
        remna_result = await remnawave_service.block_client(client_id)
        
        if not remna_result["success"]:
            audit_service.log_operation(
                db=db,
                client_id=client_id,
                action="block",
                result="fail",
                error=remna_result.get("error")
            )
            
            raise HTTPException(
                status_code=500,
                detail={"error": "Failed to block client in RemnaWave", "message": remna_result.get("error")}
            )
        
        # Обновляем статус в базе
        client.status = "blocked"
        db.commit()
        
        # Логируем операцию
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="block",
            result="success"
        )
        
        return {"message": "Client blocked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="block",
            result="fail",
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/{client_id}/unblock")
async def unblock_client(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """Разблокировка клиента"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail={"error": "Client not found", "message": f"Client with id {client_id} not found"}
        )
    
    if client.status == "active":
        return {"message": "Client is already active"}
    
    # Проверяем, не истек ли срок действия
    if client.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail={"error": "Subscription expired", "message": "Cannot unblock client with expired subscription"}
        )
    
    try:
        # Разблокируем в RemnaWave
        remna_result = await remnawave_service.unblock_client(client_id)
        
        if not remna_result["success"]:
            audit_service.log_operation(
                db=db,
                client_id=client_id,
                action="unblock",
                result="fail",
                error=remna_result.get("error")
            )
            
            raise HTTPException(
                status_code=500,
                detail={"error": "Failed to unblock client in RemnaWave", "message": remna_result.get("error")}
            )
        
        # Обновляем статус в базе
        client.status = "active"
        db.commit()
        
        # Логируем операцию
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="unblock",
            result="success"
        )
        
        return {"message": "Client unblocked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="unblock",
            result="fail",
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/{client_id}/config", response_model=ClientConfig)
async def get_client_config(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """Получение конфигурации клиента"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail={"error": "Client not found", "message": f"Client with id {client_id} not found"}
        )
    
    try:
        # Получаем конфигурацию из RemnaWave
        remna_result = await remnawave_service.get_client_config(client_id)
        
        if not remna_result["success"]:
            audit_service.log_operation(
                db=db,
                client_id=client_id,
                action="get_config",
                result="fail",
                error=remna_result.get("error")
            )
            
            raise HTTPException(
                status_code=500,
                detail={"error": "Failed to get client config", "message": remna_result.get("error")}
            )
        
        # Логируем операцию
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="get_config",
            result="success"
        )
        
        return ClientConfig(
            id=client_id,
            config_data=remna_result["data"],
            generated_at=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="get_config",
            result="fail",
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/{client_id}/config/rotate")
async def rotate_client_config(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """Перевыпуск конфигурации/ключа клиента"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail={"error": "Client not found", "message": f"Client with id {client_id} not found"}
        )
    
    try:
        # Перевыпускаем конфигурацию в RemnaWave
        remna_result = await remnawave_service.rotate_client_config(client_id)
        
        if not remna_result["success"]:
            audit_service.log_operation(
                db=db,
                client_id=client_id,
                action="config_rotate",
                result="fail",
                error=remna_result.get("error")
            )
            
            raise HTTPException(
                status_code=500,
                detail={"error": "Failed to rotate client config", "message": remna_result.get("error")}
            )
        
        # Логируем операцию
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="config_rotate",
            result="success"
        )
        
        return {
            "message": "Client config rotated successfully",
            "new_config": remna_result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_operation(
            db=db,
            client_id=client_id,
            action="config_rotate",
            result="fail",
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )
