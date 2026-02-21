import uuid
from typing import Dict, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class MockRemnaWaveService:
    """Mock сервис для демонстрации без реального RemnaWave"""
    
    def __init__(self):
        # Имитация базы данных клиентов RemnaWave
        self.clients = {}
        self.configs = {}
    
    async def create_client(self, client_id: uuid.UUID) -> Dict:
        """Создание клиента в RemnaWave (mock)"""
        try:
            # Имитируем создание клиента
            self.clients[str(client_id)] = {
                "id": str(client_id),
                "enable": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Генерируем mock конфигурацию
            self.configs[str(client_id)] = {
                "client_id": str(client_id),
                "server": "mock-server.example.com",
                "port": 443,
                "protocol": "vless",
                "uuid": str(uuid.uuid4()),
                "encryption": "none",
                "flow": "xtls-rprx-vision",
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Mock: Created client {client_id}")
            return {"success": True, "data": self.clients[str(client_id)]}
            
        except Exception as e:
            logger.error(f"Mock: Failed to create client {client_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_client_config(self, client_id: uuid.UUID) -> Dict:
        """Получение конфигурации клиента (mock)"""
        try:
            config = self.configs.get(str(client_id))
            if not config:
                return {"success": False, "error": "Client not found"}
            
            logger.info(f"Mock: Retrieved config for client {client_id}")
            return {"success": True, "data": config}
            
        except Exception as e:
            logger.error(f"Mock: Failed to get config for client {client_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def rotate_client_config(self, client_id: uuid.UUID) -> Dict:
        """Перевыпуск конфигурации клиента (mock)"""
        try:
            if str(client_id) not in self.clients:
                return {"success": False, "error": "Client not found"}
            
            # Генерируем новую конфигурацию
            new_config = {
                "client_id": str(client_id),
                "server": "mock-server.example.com",
                "port": 443,
                "protocol": "vless",
                "uuid": str(uuid.uuid4()),  # Новый UUID
                "encryption": "none",
                "flow": "xtls-rprx-vision",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "rotated": True
            }
            
            self.configs[str(client_id)] = new_config
            
            logger.info(f"Mock: Rotated config for client {client_id}")
            return {"success": True, "data": new_config}
            
        except Exception as e:
            logger.error(f"Mock: Failed to rotate config for client {client_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def block_client(self, client_id: uuid.UUID) -> Dict:
        """Блокировка клиента (mock)"""
        try:
            if str(client_id) not in self.clients:
                return {"success": False, "error": "Client not found"}
            
            self.clients[str(client_id)]["enable"] = False
            
            logger.info(f"Mock: Blocked client {client_id}")
            return {"success": True, "data": {"blocked": True}}
            
        except Exception as e:
            logger.error(f"Mock: Failed to block client {client_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def unblock_client(self, client_id: uuid.UUID) -> Dict:
        """Разблокировка клиента (mock)"""
        try:
            if str(client_id) not in self.clients:
                return {"success": False, "error": "Client not found"}
            
            self.clients[str(client_id)]["enable"] = True
            
            logger.info(f"Mock: Unblocked client {client_id}")
            return {"success": True, "data": {"unblocked": True}}
            
        except Exception as e:
            logger.error(f"Mock: Failed to unblock client {client_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def delete_client(self, client_id: uuid.UUID) -> Dict:
        """Удаление клиента (mock)"""
        try:
            # Удаляем клиента и конфигурацию
            self.clients.pop(str(client_id), None)
            self.configs.pop(str(client_id), None)
            
            logger.info(f"Mock: Deleted client {client_id}")
            return {"success": True, "data": {"deleted": True}}
            
        except Exception as e:
            logger.error(f"Mock: Failed to delete client {client_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Закрытие HTTP клиента (mock)"""
        logger.info("Mock: Service closed")


# Глобальный экземпляр mock сервиса
mock_remnawave_service = MockRemnaWaveService()
