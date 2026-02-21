from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from database import engine, Base
from routers import clients, operations
from services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаем таблицы при запуске
    Base.metadata.create_all(bind=engine)
    # Запускаем планировщик для авто-деактивации
    start_scheduler()
    yield
    # Здесь можно добавить код для очистки при выключении


app = FastAPI(
    title="RemnaWave Management API",
    description="API для управления VPN клиентами в RemnaWave",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients.router, prefix="/clients", tags=["clients"])
app.include_router(operations.router, prefix="/operations", tags=["operations"])


@app.get("/")
async def root():
    return {"message": "RemnaWave Management API", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
