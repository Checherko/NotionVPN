from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
import uuid


class ClientCreate(BaseModel):
    """Схема для создания клиента"""
    days: int = Field(gt=0, description="Количество дней подписки")


class ClientResponse(BaseModel):
    """Схема ответа для клиента"""
    id: uuid.UUID
    status: Literal["active", "blocked"]
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientExtend(BaseModel):
    """Схема для продления подписки"""
    days: int = Field(gt=0, description="Количество дней для продления")


class ClientConfig(BaseModel):
    """Схема для конфигурации клиента"""
    id: uuid.UUID
    config_data: dict  # Здесь будет конфиг RemnaWave
    generated_at: datetime

    class Config:
        from_attributes = True


class OperationCreate(BaseModel):
    """Схема для создания записи в аудите"""
    client_id: uuid.UUID
    action: str
    payload: Optional[str] = None
    result: Literal["success", "fail"]
    error: Optional[str] = None


class OperationResponse(BaseModel):
    """Схема ответа для операции аудита"""
    id: uuid.UUID
    client_id: uuid.UUID
    action: str
    payload: Optional[str]
    result: Literal["success", "fail"]
    error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Схема для ответа с ошибкой"""
    error: str
    message: str
