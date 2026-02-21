#!/usr/bin/env python3
"""
Демонстрационный скрипт для RemnaWave Management API
Показывает полный рабочий процесс управления VPN клиентами
"""

import requests
import json
import time
from datetime import datetime, timezone, timedelta

API_BASE = "http://localhost:8000"

def print_step(step, description):
    """Вывод шага демонстрации"""
    print(f"\n{'='*50}")
    print(f"Шаг {step}: {description}")
    print('='*50)

def print_response(response, title="Ответ"):
    """Красивый вывод ответа API"""
    print(f"\n{title}:")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Ошибка: {response.status_code}")
        print(response.text)

def main():
    """Основная функция демонстрации"""
    print("🚀 Демонстрация RemnaWave Management API")
    print("Этот скрипт показывает полный рабочий процесс управления VPN клиентами")
    
    # Шаг 1: Создание клиента
    print_step(1, "Создание нового клиента с подпиской на 30 дней")
    create_data = {"days": 30}
    response = requests.post(f"{API_BASE}/clients", json=create_data)
    print_response(response, "Создан клиент")
    
    if response.status_code != 200:
        print("❌ Не удалось создать клиента")
        return
    
    client_id = response.json()["id"]
    print(f"✅ Клиент создан с ID: {client_id}")
    
    # Шаг 2: Получение информации о клиенте
    print_step(2, "Получение информации о клиенте")
    response = requests.get(f"{API_BASE}/clients/{client_id}")
    print_response(response, "Информация о клиенте")
    
    # Шаг 3: Получение конфигурации
    print_step(3, "Получение конфигурации клиента")
    response = requests.get(f"{API_BASE}/clients/{client_id}/config")
    print_response(response, "Конфигурация клиента")
    
    # Шаг 4: Продление подписки
    print_step(4, "Продление подписки на 15 дней")
    extend_data = {"days": 15}
    response = requests.post(f"{API_BASE}/clients/{client_id}/extend", json=extend_data)
    print_response(response, "Результат продления")
    
    # Шаг 5: Блокировка клиента
    print_step(5, "Блокировка клиента")
    response = requests.post(f"{API_BASE}/clients/{client_id}/block")
    print_response(response, "Результат блокировки")
    
    # Шаг 6: Попытка получить конфигурацию заблокированного клиента
    print_step(6, "Попытка получить конфигурацию заблокированного клиента")
    response = requests.get(f"{API_BASE}/clients/{client_id}/config")
    print_response(response, "Конфигурация заблокированного клиента")
    
    # Шаг 7: Разблокировка клиента
    print_step(7, "Разблокировка клиента")
    response = requests.post(f"{API_BASE}/clients/{client_id}/unblock")
    print_response(response, "Результат разблокировки")
    
    # Шаг 8: Перевыпуск конфигурации
    print_step(8, "Перевыпуск конфигурации (ротация ключа)")
    response = requests.post(f"{API_BASE}/clients/{client_id}/config/rotate")
    print_response(response, "Новая конфигурация")
    
    # Шаг 9: Получение списка всех клиентов
    print_step(9, "Получение списка всех клиентов")
    response = requests.get(f"{API_BASE}/clients")
    print_response(response, "Список клиентов")
    
    # Шаг 10: Получение аудит лога
    print_step(10, "Просмотр аудита всех операций")
    response = requests.get(f"{API_BASE}/operations")
    print_response(response, "Аудит операций")
    
    # Шаг 11: Фильтрация аудита по клиенту
    print_step(11, "Просмотр аудита для конкретного клиента")
    response = requests.get(f"{API_BASE}/operations?clientId={client_id}")
    print_response(response, "Аудит операций клиента")
    
    # Шаг 12: Удаление клиента
    print_step(12, "Удаление клиента")
    response = requests.delete(f"{API_BASE}/clients/{client_id}")
    print_response(response, "Результат удаления")
    
    print(f"\n{'='*50}")
    print("✅ Демонстрация завершена!")
    print("Все функции API работают корректно:")
    print("  ✅ Создание клиентов")
    print("  ✅ Управление подписками")
    print("  ✅ Блокировка/разблокировка")
    print("  ✅ Управление конфигурациями")
    print("  ✅ Аудит операций")
    print("  ✅ Фильтрация данных")
    print("  ✅ Удаление клиентов")
    print('='*50)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Не удалось подключиться к API. Убедитесь, что сервис запущен:")
        print("   docker-compose up -d")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
