import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models import Client, Operation
from services.audit import audit_service
from database import SessionLocal, Base, engine
import uuid
import asyncio


@pytest.fixture
def db():
    """Фикстура для создания тестовой базы данных"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


class TestSchedulerLogic:
    """Тесты логики планировщика"""
    
    def test_identify_expired_clients(self, db):
        """Тест определения просроченных клиентов"""
        # Создаем активного клиента с истекшей подпиской
        expired_client = Client(
            id=uuid.uuid4(),
            status="active",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        db.add(expired_client)
        
        # Создаем активного клиента с действующей подпиской
        active_client = Client(
            id=uuid.uuid4(),
            status="active",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
        db.add(active_client)
        
        # Создаем заблокированного клиента с истекшей подпиской
        blocked_expired_client = Client(
            id=uuid.uuid4(),
            status="blocked",
            expires_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        db.add(blocked_expired_client)
        
        db.commit()
        
        # Ищем просроченных активных клиентов
        expired_clients = db.query(Client).filter(
            Client.status == "active",
            Client.expires_at < datetime.now(timezone.utc)
        ).all()
        
        # Должен быть только 1 клиент (expired_client)
        assert len(expired_clients) == 1
        assert expired_clients[0].id == expired_client.id
        assert expired_clients[0].status == "active"
    
    def test_audit_logging_for_deactivation(self, db):
        """Тест логирования деактивации в аудит"""
        # Сначала создаем клиента в базе
        client = Client(
            id=uuid.uuid4(),
            status="active",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        db.add(client)
        db.commit()
        
        # Логируем успешную деактивацию
        operation = audit_service.log_operation(
            db=db,
            client_id=client.id,
            action="auto_deactivate",
            result="success"
        )
        
        assert operation.action == "auto_deactivate"
        assert operation.result == "success"
        assert operation.error is None
        
        # Логируем неудачную деактивацию
        failed_operation = audit_service.log_operation(
            db=db,
            client_id=client.id,
            action="auto_deactivate",
            result="fail",
            error="Connection timeout"
        )
        
        assert failed_operation.action == "auto_deactivate"
        assert failed_operation.result == "fail"
        assert failed_operation.error == "Connection timeout"
    
    def test_client_status_change(self, db):
        """Тест изменения статуса клиента"""
        client = Client(
            id=uuid.uuid4(),
            status="active",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        db.add(client)
        db.commit()
        
        # Меняем статус на заблокированный
        client.status = "blocked"
        db.commit()
        db.refresh(client)
        
        assert client.status == "blocked"
        
        # Проверяем, что в аудит записалась операция
        audit_service.log_operation(
            db=db,
            client_id=client.id,
            action="auto_deactivate",
            result="success"
        )
        
        operations = audit_service.get_operations(db, client.id)
        deactivation_ops = [op for op in operations if op.action == "auto_deactivate"]
        assert len(deactivation_ops) == 1
        assert deactivation_ops[0].result == "success"
