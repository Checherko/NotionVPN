import httpx
from typing import Dict, Optional
from pydantic_settings import BaseSettings
import json
import uuid
import logging

logger = logging.getLogger(__name__)

class RemnaWaveSettings(BaseSettings):
    remnawave_url: str = "http://localhost:8080"
    use_mock: bool = True  # Использовать mock для демонстрации
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = RemnaWaveSettings()


class RemnaWaveService:
    """Сервис для взаимодействия с RemnaWave API"""
    
    def __init__(self):
        self.base_url = settings.remnawave_url
        self.use_mock = settings.use_mock
        
        if not self.use_mock:
            self.client = httpx.AsyncClient(timeout=30.0)
        else:
            # Импортируем mock сервис
            from .mock_remnawave import mock_remnawave_service
            self.mock_service = mock_remnawave_service
    
    async def create_client(self, client_id: uuid.UUID) -> Dict:
        """Создание клиента в RemnaWave"""
        if self.use_mock:
            return await self.mock_service.create_client(client_id)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/clients",
                json={
                    "id": str(client_id),
                    "enable": True
                }
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except httpx.HTTPError as e:
            logger.error(f"RemnaWave API error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_client_config(self, client_id: uuid.UUID) -> Dict:
        """Получение конфигурации клиента"""
        if self.use_mock:
            return await self.mock_service.get_client_config(client_id)
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/clients/{client_id}/config"
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except httpx.HTTPError as e:
            logger.error(f"RemnaWave API error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def rotate_client_config(self, client_id: uuid.UUID) -> Dict:
        """Перевыпуск конфигурации клиента"""
        if self.use_mock:
            return await self.mock_service.rotate_client_config(client_id)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/clients/{client_id}/config/rotate"
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except httpx.HTTPError as e:
            logger.error(f"RemnaWave API error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def block_client(self, client_id: uuid.UUID) -> Dict:
        """Блокировка клиента"""
        if self.use_mock:
            return await self.mock_service.block_client(client_id)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/clients/{client_id}/block"
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except httpx.HTTPError as e:
            logger.error(f"RemnaWave API error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def unblock_client(self, client_id: uuid.UUID) -> Dict:
        """Разблокировка клиента"""
        if self.use_mock:
            return await self.mock_service.unblock_client(client_id)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/clients/{client_id}/unblock"
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except httpx.HTTPError as e:
            logger.error(f"RemnaWave API error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def delete_client(self, client_id: uuid.UUID) -> Dict:
        """Удаление клиента"""
        if self.use_mock:
            return await self.mock_service.delete_client(client_id)
        
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/clients/{client_id}"
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except httpx.HTTPError as e:
            logger.error(f"RemnaWave API error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Закрытие HTTP клиента"""
        if not self.use_mock:
            await self.client.aclose()


# Глобальный экземпляр сервиса
remnawave_service = RemnaWaveService()
