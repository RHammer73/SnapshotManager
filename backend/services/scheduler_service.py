"""APScheduler-Integration für geplante Backup-Jobs."""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import AsyncSessionLocal
from models import Schedule, BackupJob
from sqlalchemy import select, update

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")


async def _run_scheduled_job(schedule_id: int) -> None:
    from services.backup_service import is_backup_running, start_backup

    if is_backup_running():
        logger.warning(f"Schedule {schedule_id}: Backup läuft bereits – wird übersprungen")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
        schedule = result.scalar_one_or_none()
        if not schedule or not schedule.enabled:
            return

        job = BackupJob(
            host_id=schedule.host_id,
            triggered_by="schedule",
            schedule_id=schedule_id,
            shutdown_after=schedule.shutdown_after,
            status="pending",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

        await db.execute(
            update(Schedule)
            .where(Schedule.id == schedule_id)
            .values(last_run_at=datetime.utcnow())
        )
        await db.commit()

    logger.info(f"Schedule {schedule_id}: Starte Job #{job_id}")
    await start_backup(job_id)


def _make_apscheduler_job_id(schedule_id: int) -> str:
    return f"schedule_{schedule_id}"


async def load_schedules() -> None:
    """Lädt alle aktivierten Schedules beim Start aus der DB."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Schedule).where(Schedule.enabled == True))
        schedules = result.scalars().all()

    for schedule in schedules:
        add_schedule(schedule.id, schedule.cron_expression)
    logger.info(f"{len(schedules)} Schedules geladen")


def add_schedule(schedule_id: int, cron_expression: str) -> None:
    job_id = _make_apscheduler_job_id(schedule_id)
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Ungültiger Cron-Ausdruck: {cron_expression}")

    minute, hour, day, month, day_of_week = parts
    trigger = CronTrigger(
        minute=minute, hour=hour,
        day=day, month=month, day_of_week=day_of_week,
        timezone="UTC"
    )

    if scheduler.get_job(job_id):
        scheduler.reschedule_job(job_id, trigger=trigger)
    else:
        scheduler.add_job(
            _run_scheduled_job,
            trigger=trigger,
            args=[schedule_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300,
        )


def remove_schedule(schedule_id: int) -> None:
    job_id = _make_apscheduler_job_id(schedule_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def get_next_run(schedule_id: int) -> datetime | None:
    job_id = _make_apscheduler_job_id(schedule_id)
    job = scheduler.get_job(job_id)
    if job and job.next_run_time:
        return job.next_run_time.replace(tzinfo=None)
    return None


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
