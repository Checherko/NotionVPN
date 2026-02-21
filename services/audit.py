from sqlalchemy.orm import Session
from models import Operation, Client
from schemas import OperationCreate
from typing import Optional
import json
import uuid


class AuditService:
    """Сервис для аудита операций"""
    
    @staticmethod
    def log_operation(
        db: Session,
        client_id: uuid.UUID,
        action: str,
        payload: Optional[dict] = None,
        result: str = "success",
        error: Optional[str] = None
    ) -> Operation:
        """Логирование операции в базу данных"""
        
        operation = Operation(
            client_id=client_id,
            action=action,
            payload=json.dumps(payload) if payload else None,
            result=result,
            error=error
        )
        
        db.add(operation)
        db.commit()
        db.refresh(operation)
        
        return operation
    
    @staticmethod
    def get_operations(db: Session, client_id: Optional[uuid.UUID] = None) -> list[Operation]:
        """Получение списка операций"""
        query = db.query(Operation)
        
        if client_id:
            query = query.filter(Operation.client_id == client_id)
        
        return query.order_by(Operation.created_at.desc()).all()


# Глобальный экземпляр сервиса
audit_service = AuditService()
