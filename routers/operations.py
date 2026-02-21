from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from database import get_db
from models import Operation
from schemas import OperationResponse
from services.audit import audit_service

router = APIRouter()


@router.get("/", response_model=List[OperationResponse])
def get_operations(
    client_id: Optional[uuid.UUID] = Query(None, description="Фильтр по ID клиента"),
    db: Session = Depends(get_db)
):
    """Получение списка операций с фильтрацией по клиенту"""
    
    operations = audit_service.get_operations(db, client_id)
    return operations
