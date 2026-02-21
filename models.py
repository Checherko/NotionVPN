from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), nullable=False, default="active")  # active, blocked
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связь с операциями
    operations = relationship("Operation", back_populates="client")


class Operation(Base):
    __tablename__ = "operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(50), nullable=False)  # create, extend, block, unblock, delete, config_rotate
    payload = Column(Text)  # JSON строка с параметрами операции
    result = Column(String(10), nullable=False)  # success, fail
    error = Column(Text)  # Текст ошибки если result = fail
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связь с клиентом
    client = relationship("Client", back_populates="operations")
