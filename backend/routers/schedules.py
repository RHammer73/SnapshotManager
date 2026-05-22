from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Schedule
from schemas import ScheduleCreate, ScheduleUpdate, ScheduleRead
from services import scheduler_service

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleRead])
async def list_schedules(
    host_id: int | None = None,
    db: AsyncSession = Depends(get_db)
):
    q = select(Schedule).order_by(Schedule.id)
    if host_id is not None:
        q = q.where(Schedule.host_id == host_id)
    result = await db.execute(q)
    schedules = result.scalars().all()
    # Nächste Ausführung aktualisieren
    for s in schedules:
        next_run = scheduler_service.get_next_run(s.id)
        if next_run:
            s.next_run_at = next_run
    return schedules


@router.post("", response_model=ScheduleRead, status_code=201)
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    # Cron-Ausdruck validieren
    parts = data.cron_expression.strip().split()
    if len(parts) != 5:
        raise HTTPException(400, "Ungültiger Cron-Ausdruck (erwartet: 5 Felder, z.B. '0 2 * * *')")

    schedule = Schedule(**data.model_dump())
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    if schedule.enabled:
        scheduler_service.add_schedule(schedule.id, schedule.cron_expression)
        schedule.next_run_at = scheduler_service.get_next_run(schedule.id)
        await db.commit()

    return schedule


@router.get("/{schedule_id}", response_model=ScheduleRead)
async def get_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Schedule nicht gefunden")
    return s


@router.put("/{schedule_id}", response_model=ScheduleRead)
async def update_schedule(
    schedule_id: int, data: ScheduleUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(404, "Schedule nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    if "cron_expression" in update_data:
        parts = update_data["cron_expression"].strip().split()
        if len(parts) != 5:
            raise HTTPException(400, "Ungültiger Cron-Ausdruck")

    for key, value in update_data.items():
        setattr(schedule, key, value)

    await db.commit()
    await db.refresh(schedule)

    # APScheduler aktualisieren
    if schedule.enabled:
        scheduler_service.add_schedule(schedule.id, schedule.cron_expression)
        schedule.next_run_at = scheduler_service.get_next_run(schedule.id)
    else:
        scheduler_service.remove_schedule(schedule.id)
    await db.commit()

    return schedule


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(404, "Schedule nicht gefunden")

    scheduler_service.remove_schedule(schedule_id)
    await db.delete(schedule)
    await db.commit()
