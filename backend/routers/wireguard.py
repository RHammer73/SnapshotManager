from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import WireguardConfig
from schemas import WireguardCreate, WireguardUpdate, WireguardRead
from services import wireguard_service

router = APIRouter(prefix="/api/wireguard", tags=["wireguard"])


@router.get("", response_model=list[WireguardRead])
async def list_configs(
    host_id: int | None = None,
    db: AsyncSession = Depends(get_db)
):
    q = select(WireguardConfig)
    if host_id is not None:
        q = q.where(WireguardConfig.host_id == host_id)
    result = await db.execute(q)
    configs = result.scalars().all()
    # Tatsächlichen Status prüfen
    for c in configs:
        active = wireguard_service.is_active(c.interface_name)
        c.status = "active" if active else "inactive"
    return configs


@router.post("", response_model=WireguardRead, status_code=201)
async def create_config(data: WireguardCreate, db: AsyncSession = Depends(get_db)):
    # Prüfen ob Interface-Name schon existiert
    existing = await db.execute(
        select(WireguardConfig).where(WireguardConfig.interface_name == data.interface_name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Interface '{data.interface_name}' existiert bereits")

    config = WireguardConfig(**data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/{config_id}", response_model=WireguardRead)
async def get_config(config_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WireguardConfig).where(WireguardConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "WireGuard-Konfiguration nicht gefunden")
    config.status = "active" if wireguard_service.is_active(config.interface_name) else "inactive"
    return config


@router.put("/{config_id}", response_model=WireguardRead)
async def update_config(config_id: int, data: WireguardUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WireguardConfig).where(WireguardConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "WireGuard-Konfiguration nicht gefunden")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/{config_id}", status_code=204)
async def delete_config(config_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WireguardConfig).where(WireguardConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "WireGuard-Konfiguration nicht gefunden")

    # Interface herunterfahren falls aktiv
    if wireguard_service.is_active(config.interface_name):
        try:
            wireguard_service.interface_down(config.interface_name)
        except Exception:
            pass
    wireguard_service.remove_config(config.interface_name)

    await db.delete(config)
    await db.commit()


@router.post("/{config_id}/up")
async def interface_up(config_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WireguardConfig).where(WireguardConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "WireGuard-Konfiguration nicht gefunden")
    try:
        wireguard_service.write_config(config.interface_name, config.config_content)
        wireguard_service.interface_up(config.interface_name)
        config.status = "active"
        await db.commit()
        return {"status": "active", "interface": config.interface_name}
    except Exception as e:
        raise HTTPException(500, f"WireGuard up fehlgeschlagen: {e}")


@router.post("/{config_id}/down")
async def interface_down(config_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WireguardConfig).where(WireguardConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "WireGuard-Konfiguration nicht gefunden")
    try:
        wireguard_service.interface_down(config.interface_name)
        config.status = "inactive"
        await db.commit()
        return {"status": "inactive", "interface": config.interface_name}
    except Exception as e:
        raise HTTPException(500, f"WireGuard down fehlgeschlagen: {e}")


@router.get("/{config_id}/status")
async def get_status(config_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WireguardConfig).where(WireguardConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "WireGuard-Konfiguration nicht gefunden")
    status = wireguard_service.get_status(config.interface_name)
    return status
