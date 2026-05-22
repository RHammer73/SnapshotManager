from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Host, VM
from schemas import HostCreate, HostUpdate, HostReadSafe
from services import proxmox_service

router = APIRouter(prefix="/api/hosts", tags=["hosts"])


@router.get("", response_model=list[HostReadSafe])
async def list_hosts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Host).order_by(Host.name))
    return result.scalars().all()


@router.post("", response_model=HostReadSafe, status_code=201)
async def create_host(data: HostCreate, db: AsyncSession = Depends(get_db)):
    host = Host(**data.model_dump())
    db.add(host)
    await db.commit()
    await db.refresh(host)
    return host


@router.get("/{host_id}", response_model=HostReadSafe)
async def get_host(host_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host nicht gefunden")
    return host


@router.put("/{host_id}", response_model=HostReadSafe)
async def update_host(host_id: int, data: HostUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host nicht gefunden")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(host, key, value)
    await db.commit()
    await db.refresh(host)
    return host


@router.delete("/{host_id}", status_code=204)
async def delete_host(host_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host nicht gefunden")
    await db.delete(host)
    await db.commit()


@router.post("/{host_id}/test-connection")
async def test_connection(host_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host nicht gefunden")
    info = proxmox_service.test_connection(
        host.ip_address, host.ssh_port, host.ssh_user,
        host.auth_type, host.ssh_password, host.ssh_private_key
    )
    return info


@router.post("/{host_id}/discover-vms")
async def discover_vms(host_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host nicht gefunden")

    try:
        ssh = proxmox_service.get_ssh_client(
            host.ip_address, host.ssh_port, host.ssh_user,
            host.auth_type, host.ssh_password, host.ssh_private_key
        )
        discovered = proxmox_service.discover_vms(ssh, host.proxmox_pool)
        ssh.close()
    except Exception as e:
        raise HTTPException(500, f"VM-Discovery fehlgeschlagen: {e}")

    # Bestehende VMs laden
    existing_result = await db.execute(select(VM).where(VM.host_id == host_id))
    existing_vms = {vm.vmid: vm for vm in existing_result.scalars().all()}

    created = 0
    updated = 0
    for vm_data in discovered:
        vmid = vm_data["vmid"]
        if vmid in existing_vms:
            # Datasets aktualisieren, Namen ggf. neu
            vm = existing_vms[vmid]
            vm.zfs_datasets = vm_data["zfs_datasets"]
            if vm.name != vm_data["name"]:
                vm.name = vm_data["name"]
            updated += 1
        else:
            # Neue VM anlegen (backup_order = letzter+1)
            max_order = max((v.backup_order for v in existing_vms.values()), default=0)
            vm = VM(
                host_id=host_id,
                vmid=vmid,
                name=vm_data["name"],
                vm_type=vm_data["vm_type"],
                zfs_datasets=vm_data["zfs_datasets"],
                backup_order=max_order + 1,
            )
            db.add(vm)
            existing_vms[vmid] = vm
            created += 1

    await db.commit()
    return {"discovered": len(discovered), "created": created, "updated": updated}
