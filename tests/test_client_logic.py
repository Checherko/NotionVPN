import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models import Client, Operation
from services.audit import audit_service
from database import SessionLocal, Base, engine
import uuid


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


@pytest.fixture
def sample_client(db):
    """Фикстура для создания тестового клиента"""
    client = Client(
        id=uuid.uuid4(),
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


class TestClientLogic:
    """Тесты бизнес-логики клиентов"""
    
    def test_client_creation(self, db):
        """Тест создания клиента"""
        client_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(days=15)
        
        client = Client(
            id=client_id,
            status="active",
            expires_at=expires_at
        )
        
        db.add(client)
        db.commit()
        db.refresh(client)
        
        assert client.id == client_id
        assert client.status == "active"
        assert client.expires_at == expires_at
        assert client.created_at is not None
        assert client.updated_at is not None
    
    def test_extend_subscription_future_date(self, sample_client, db):
        """Тест продления подписки с будущей датой окончания"""
        original_expires = sample_client.expires_at
        extend_days = 10
        
        # Продляем подписку
        sample_client.expires_at = original_expires + timedelta(days=extend_days)
        db.commit()
        db.refresh(sample_client)
        
        expected_expires = original_expires + timedelta(days=extend_days)
        assert sample_client.expires_at == expected_expires
    
    def test_extend_subscription_expired_date(self, sample_client, db):
        """Тест продления подписки с истекшей датой"""
        # Устанавливаем дату в прошлом
        past_date = datetime.now(timezone.utc) - timedelta(days=5)
        sample_client.expires_at = past_date
        db.commit()
        
        # Продляем на 10 дней от текущей даты
        extend_days = 10
        expected_expires = datetime.now(timezone.utc) + timedelta(days=extend_days)
        
        sample_client.expires_at = expected_expires
        db.commit()
        db.refresh(sample_client)
        
        # Проверяем, что дата установлена от текущего момента
        time_diff = sample_client.expires_at - datetime.now(timezone.utc)
        assert abs(time_diff.total_seconds() - timedelta(days=extend_days).total_seconds()) < 60  # Погрешность 1 минута
    
    def test_block_client(self, sample_client, db):
        """Тест блокировки клиента"""
        assert sample_client.status == "active"
        
        sample_client.status = "blocked"
        db.commit()
        db.refresh(sample_client)
        
        assert sample_client.status == "blocked"
    
    def test_unblock_client_with_valid_subscription(self, sample_client, db):
        """Тест разблокировки клиента с действующей подпиской"""
        # Блокируем клиента
        sample_client.status = "blocked"
        db.commit()
        
        # Убеждаемся, что подписка действительна
        assert sample_client.expires_at > datetime.now(timezone.utc)
        
        # Разблокируем
        sample_client.status = "active"
        db.commit()
        db.refresh(sample_client)
        
        assert sample_client.status == "active"
    
    def test_audit_operation_logging(self, db, sample_client):
        """Тест логирования операций в аудит"""
        operation = audit_service.log_operation(
            db=db,
            client_id=sample_client.id,
            action="test_action",
            payload={"test": "data"},
            result="success"
        )
        
        assert operation.client_id == sample_client.id
        assert operation.action == "test_action"
        assert operation.result == "success"
        assert operation.created_at is not None
        
        # Проверяем получение операций
        operations = audit_service.get_operations(db, sample_client.id)
        assert len(operations) >= 1
        assert operations[0].client_id == sample_client.id
    
    def test_get_operations_filtered_by_client(self, db, sample_client):
        """Тест фильтрации операций по клиенту"""
        # Создаем операции для разных клиентов
        client2 = Client(
            id=uuid.uuid4(),
            status="active",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        db.add(client2)
        db.commit()
        
        audit_service.log_operation(db, sample_client.id, "action1", result="success")
        audit_service.log_operation(db, sample_client.id, "action2", result="success")
        audit_service.log_operation(db, client2.id, "action3", result="success")
        
        # Получаем операции только для sample_client
        operations = audit_service.get_operations(db, sample_client.id)
        
        # Должны быть только 2 операции для sample_client
        client_operations = [op for op in operations if op.client_id == sample_client.id]
        assert len(client_operations) == 2
        
        # Все операции должны принадлежать sample_client
        for op in operations:
            assert op.client_id == sample_client.id
