# database.py
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String

DATABASE_URL = os.getenv('DATABASE_URL')  # Например, 'postgresql+asyncpg://user:password@localhost/dbname'

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

class UserData(Base):
    __tablename__ = 'user_data'

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    fio = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    school_class = Column(String, nullable=False)
    prof_prob = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    review = Column(String, nullable=True)
