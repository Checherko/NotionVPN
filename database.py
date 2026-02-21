from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/remnawave"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
