from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        from models import (  # noqa: F401
            Host, WireguardConfig, VM, BackupJob, BackupJobVM,
            BackupLog, Schedule, StoredSnapshot, AppSetting
        )
        await conn.run_sync(Base.metadata.create_all)
