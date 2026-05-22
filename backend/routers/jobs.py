import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from database import get_db
from models import BackupJob, BackupJobVM, BackupLog
from schemas import JobCreate, JobRead, JobLogRead
from services import backup_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
async def list_jobs(
    host_id: int | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    q = select(BackupJob).order_by(BackupJob.id.desc()).limit(limit)
    if host_id is not None:
        q = q.where(BackupJob.host_id == host_id)
    result = await db.execute(q)
    jobs = result.scalars().all()
    # job_vms laden
    for job in jobs:
        await db.refresh(job, ["job_vms"])
    return jobs


@router.post("", response_model=JobRead, status_code=201)
async def create_job(data: JobCreate, db: AsyncSession = Depends(get_db)):
    if backup_service.is_backup_running():
        raise HTTPException(409, "Ein Backup-Job läuft bereits. Bitte warten.")

    job = BackupJob(
        host_id=data.host_id,
        triggered_by="manual",
        shutdown_after=data.shutdown_after,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await backup_service.start_backup(job.id)
    await db.refresh(job, ["job_vms"])
    return job


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BackupJob).where(BackupJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job nicht gefunden")
    await db.refresh(job, ["job_vms"])
    return job


@router.get("/{job_id}/logs", response_model=list[JobLogRead])
async def get_job_logs(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BackupLog)
        .where(BackupLog.job_id == job_id)
        .order_by(BackupLog.id)
    )
    return result.scalars().all()


@router.get("/{job_id}/stream")
async def stream_job_progress(job_id: int):
    """SSE-Endpoint für Echtzeit-Fortschritt."""
    queue = backup_service.get_job_queue(job_id)

    async def generator():
        # Wenn kein aktiver Queue, sende aktuellen Status aus DB
        if queue is None:
            yield {
                "data": json.dumps({"done": True, "overall_progress": 100})
            }
            return

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield {"data": json.dumps(event)}
                if event.get("done"):
                    break
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"ping": True})}

    return EventSourceResponse(generator())


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BackupJob).where(BackupJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job nicht gefunden")
    if job.status not in ("pending", "running"):
        raise HTTPException(400, f"Job kann nicht abgebrochen werden (Status: {job.status})")

    job.status = "cancelled"
    job.finished_at = datetime.utcnow()
    await db.commit()

    q = backup_service.get_job_queue(job_id)
    if q:
        await q.put({"done": True, "error": "Abgebrochen"})

    return {"status": "cancelled"}


@router.get("/status/running")
async def get_running_status():
    return {"running": backup_service.is_backup_running()}
