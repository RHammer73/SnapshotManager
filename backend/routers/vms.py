from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import VM
from schemas import VMRead, VMUpdate, VMReorderItem

router = APIRouter(prefix="/api/vms", tags=["vms"])


@router.get("", response_model=list[VMRead])
async def list_vms(host_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VM).where(VM.host_id == host_id).order_by(VM.backup_order)
    )
    return result.scalars().all()


@router.get("/{vm_id}", response_model=VMRead)
async def get_vm(vm_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(404, "VM nicht gefunden")
    return vm


@router.put("/reorder")
async def reorder_vms(items: list[VMReorderItem], db: AsyncSession = Depends(get_db)):
    for item in items:
        result = await db.execute(select(VM).where(VM.id == item.id))
        vm = result.scalar_one_or_none()
        if vm:
            vm.backup_order = item.backup_order
    await db.commit()
    return {"updated": len(items)}


@router.put("/{vm_id}", response_model=VMRead)
async def update_vm(vm_id: int, data: VMUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(404, "VM nicht gefunden")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(vm, key, value)
    await db.commit()
    await db.refresh(vm)
    return vm
