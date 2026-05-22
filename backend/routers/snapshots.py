from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import StoredSnapshot
from schemas import SnapshotRead
from services.zfs_service import local_destroy_snapshot

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


@router.get("", response_model=list[SnapshotRead])
async def list_snapshots(
    vm_id: int | None = None,
    db: AsyncSession = Depends(get_db)
):
    q = select(StoredSnapshot).order_by(StoredSnapshot.created_at.desc())
    if vm_id is not None:
        q = q.where(StoredSnapshot.vm_id == vm_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.delete("/{snapshot_id}", status_code=204)
async def delete_snapshot(snapshot_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StoredSnapshot).where(StoredSnapshot.id == snapshot_id))
    snap = result.scalar_one_or_none()
    if not snap:
        raise HTTPException(404, "Snapshot nicht gefunden")

    try:
        local_destroy_snapshot(snap.zfs_path)
    except Exception as e:
        raise HTTPException(500, f"ZFS destroy fehlgeschlagen: {e}")

    await db.delete(snap)
    await db.commit()
