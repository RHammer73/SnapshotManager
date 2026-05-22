import subprocess
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AppSetting
from schemas import SettingRead, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "app_name": "SnapshotManager",
    "shutdown_delay_seconds": "10",
    "log_retention_days": "90",
}


@router.get("", response_model=list[SettingRead])
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSetting))
    settings = {s.key: s for s in result.scalars().all()}

    # Defaults auffüllen
    for key, default_val in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = AppSetting(key=key, value=default_val)

    return list(settings.values())


@router.put("")
async def update_settings(data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSetting))
    existing = {s.key: s for s in result.scalars().all()}

    for key, value in data.settings.items():
        if key in existing:
            existing[key].value = value
        else:
            db.add(AppSetting(key=key, value=value))

    await db.commit()
    return {"updated": len(data.settings)}


@router.post("/system/shutdown")
async def shutdown_server():
    """Fährt den Backupserver herunter."""
    import asyncio
    asyncio.create_task(_delayed_shutdown())
    return {"message": "Server wird in 10 Sekunden heruntergefahren..."}


async def _delayed_shutdown():
    import asyncio
    await asyncio.sleep(10)
    subprocess.run(["shutdown", "-h", "now"], check=False)
