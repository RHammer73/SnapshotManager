"""Haupt-Backup-Orchestrierung mit Job-Lock und SSE-Fortschritt."""
import asyncio
import json
import subprocess
from datetime import datetime
from typing import Optional, Callable, Awaitable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import BackupJob, BackupJobVM, BackupLog, StoredSnapshot, VM, Host, WireguardConfig
from services import proxmox_service, wireguard_service, zfs_service
from config import settings

# Globaler Lock: verhindert parallele Backup-Jobs
_backup_lock = asyncio.Lock()

# SSE-Queues pro Job-ID
_job_queues: dict[int, asyncio.Queue] = {}


def is_backup_running() -> bool:
    return _backup_lock.locked()


def get_job_queue(job_id: int) -> Optional[asyncio.Queue]:
    return _job_queues.get(job_id)


def register_job_queue(job_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _job_queues[job_id] = q
    return q


def unregister_job_queue(job_id: int) -> None:
    _job_queues.pop(job_id, None)


async def _emit(job_id: int, event: dict) -> None:
    q = _job_queues.get(job_id)
    if q:
        await q.put(event)


async def _log(db: AsyncSession, job_id: int, message: str, level: str = "info", vm_id: Optional[int] = None) -> None:
    entry = BackupLog(job_id=job_id, vm_id=vm_id, level=level, message=message)
    db.add(entry)
    await db.commit()
    await _emit(job_id, {"log": message, "level": level})


async def _update_job(db: AsyncSession, job_id: int, **kwargs) -> None:
    await db.execute(update(BackupJob).where(BackupJob.id == job_id).values(**kwargs))
    await db.commit()


async def _update_job_vm(db: AsyncSession, jvm_id: int, **kwargs) -> None:
    await db.execute(update(BackupJobVM).where(BackupJobVM.id == jvm_id).values(**kwargs))
    await db.commit()


async def start_backup(job_id: int) -> None:
    """Startet den Backup-Job asynchron (non-blocking)."""
    if _backup_lock.locked():
        raise RuntimeError("Ein Backup-Job läuft bereits. Bitte warten.")
    asyncio.create_task(_run_backup_locked(job_id))


async def _run_backup_locked(job_id: int) -> None:
    async with _backup_lock:
        register_job_queue(job_id)
        try:
            await _execute_backup(job_id)
        finally:
            # Sende done-Event an alle wartenden SSE-Clients
            await _emit(job_id, {"done": True, "overall_progress": 100})
            await asyncio.sleep(2)
            unregister_job_queue(job_id)


async def _execute_backup(job_id: int) -> None:
    async with AsyncSessionLocal() as db:
        # Job laden
        result = await db.execute(
            select(BackupJob).where(BackupJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            return

        # Host laden
        host_result = await db.execute(select(Host).where(Host.id == job.host_id))
        host = host_result.scalar_one_or_none()
        if not host:
            await _update_job(db, job_id, status="failed", error_message="Host nicht gefunden",
                              finished_at=datetime.utcnow())
            return

        # VMs laden (enabled, sortiert nach backup_order)
        vms_result = await db.execute(
            select(VM)
            .where(VM.host_id == host.id, VM.enabled == True)
            .order_by(VM.backup_order)
        )
        vms = vms_result.scalars().all()

        if not vms:
            await _update_job(db, job_id, status="completed", progress=100,
                              current_step="Keine VMs zum Sichern konfiguriert",
                              finished_at=datetime.utcnow())
            await _emit(job_id, {"overall_progress": 100, "step": "Keine VMs konfiguriert", "done": True})
            return

        # WireGuard-Config laden
        wg_result = await db.execute(
            select(WireguardConfig).where(WireguardConfig.host_id == host.id)
        )
        wg_config = wg_result.scalar_one_or_none()

        vm_total = len(vms)
        wg_interface = None

        await _update_job(db, job_id, status="running", started_at=datetime.utcnow(),
                          progress=2, current_step="Starte Backup-Job...")

    # ── Schritt 1: WireGuard verbinden ────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        if wg_config:
            await _emit(job_id, {
                "overall_progress": 3, "step": "Verbinde WireGuard VPN...",
                "log": f"WireGuard-Interface: {wg_config.interface_name}", "level": "info"
            })
            await _log(db, job_id, f"Verbinde WireGuard: {wg_config.interface_name}")
            try:
                wireguard_service.write_config(wg_config.interface_name, wg_config.config_content)
                wireguard_service.interface_up(wg_config.interface_name)
                wg_interface = wg_config.interface_name
                await _update_job(db, job_id, progress=5, current_step="WireGuard verbunden")
                await _log(db, job_id, "WireGuard VPN verbunden")
                await _emit(job_id, {"overall_progress": 5, "step": "VPN verbunden"})
            except Exception as e:
                await _log(db, job_id, f"WireGuard-Fehler: {e}", "error")
                await _update_job(db, job_id, status="failed",
                                  error_message=f"WireGuard-Verbindung fehlgeschlagen: {e}",
                                  finished_at=datetime.utcnow())
                await _emit(job_id, {"done": True, "error": str(e)})
                return

    # ── Schritt 2: SSH-Verbindung aufbauen ────────────────────────────────────
    try:
        ssh_client = proxmox_service.get_ssh_client(
            ip=host.ip_address,
            port=host.ssh_port,
            user=host.ssh_user,
            auth_type=host.auth_type,
            password=host.ssh_password,
            private_key=host.ssh_private_key,
        )
    except Exception as e:
        async with AsyncSessionLocal() as db:
            await _log(db, job_id, f"SSH-Verbindung fehlgeschlagen: {e}", "error")
            await _update_job(db, job_id, status="failed",
                              error_message=f"SSH-Verbindung fehlgeschlagen: {e}",
                              finished_at=datetime.utcnow())
        if wg_interface:
            _safe_wg_down(wg_interface)
        await _emit(job_id, {"done": True, "error": str(e)})
        return

    # ── Schritt 3: VMs sichern ────────────────────────────────────────────────
    overall_success = True
    try:
        for vm_index, vm in enumerate(vms):
            vm_progress_base = 10 + int((vm_index / vm_total) * 80)
            vm_progress_step = int(80 / vm_total)

            async with AsyncSessionLocal() as db:
                # BackupJobVM anlegen
                jvm = BackupJobVM(
                    job_id=job_id,
                    vm_id=vm.id,
                    status="running",
                    started_at=datetime.utcnow(),
                )
                db.add(jvm)
                await db.commit()
                await db.refresh(jvm)
                jvm_id = jvm.id

                await _update_job(
                    db, job_id,
                    progress=vm_progress_base,
                    current_step=f"Sichere VM: {vm.name} ({vm_index + 1}/{vm_total})"
                )
                await _log(db, job_id, f"━━ Starte VM: {vm.name} (vmid={vm.vmid}, Typ={vm.vm_type})", vm_id=vm.id)

            await _emit(job_id, {
                "overall_progress": vm_progress_base,
                "current_vm": vm.name,
                "vm_index": vm_index + 1,
                "vm_total": vm_total,
                "vm_progress": 0,
                "step": f"VM {vm_index + 1}/{vm_total}: {vm.name}",
            })

            datasets = json.loads(vm.zfs_datasets or "[]")
            if not datasets:
                async with AsyncSessionLocal() as db:
                    await _log(db, job_id, f"Keine ZFS-Datasets für VM {vm.name} gefunden – überspringe", "warning", vm.id)
                    await _update_job_vm(db, jvm_id, status="skipped", finished_at=datetime.utcnow())
                continue

            snapshot_name = datetime.utcnow().strftime("backup-%Y%m%d-%H%M%S")
            total_size = 0
            vm_ok = True

            # Parent-Dataset sicherstellen (OpenZFS erstellt keine Zwischendatasets)
            parent_dataset = f"{host.backup_pool}/{vm.vmid}"
            if not zfs_service.local_dataset_exists(parent_dataset):
                zfs_service.local_create_dataset(parent_dataset)

            for ds_index, dataset in enumerate(datasets):
                ds_progress_base = int((ds_index / len(datasets)) * 60)
                local_dataset = f"{host.backup_pool}/{vm.vmid}/{dataset.split('/')[-1]}"

                # ── Snapshot erstellen ────────────────────────────────────────
                async with AsyncSessionLocal() as db:
                    await _log(db, job_id, f"  Erstelle Snapshot: {dataset}@{snapshot_name}", vm_id=vm.id)
                await _emit(job_id, {
                    "overall_progress": vm_progress_base + int(ds_progress_base * vm_progress_step / 100),
                    "current_vm": vm.name,
                    "vm_index": vm_index + 1,
                    "vm_total": vm_total,
                    "vm_progress": ds_progress_base,
                    "step": f"Erstelle Snapshot: {dataset.split('/')[-1]}",
                })

                try:
                    await zfs_service.ssh_create_snapshot(ssh_client, dataset, snapshot_name)
                except Exception as e:
                    async with AsyncSessionLocal() as db:
                        await _log(db, job_id, f"  Snapshot-Fehler: {e}", "error", vm.id)
                    vm_ok = False
                    continue

                # ── ZFS Send/Receive ──────────────────────────────────────────
                # Inkrementell wenn möglich: letzten gemeinsamen Snapshot ermitteln
                prev_snapshot_name = None
                if zfs_service.local_dataset_exists(local_dataset):
                    last_local = zfs_service.local_get_latest_snapshot(local_dataset)
                    if last_local and await zfs_service.ssh_snapshot_exists(
                        ssh_client, f"{dataset}@{last_local}"
                    ):
                        prev_snapshot_name = last_local
                    else:
                        # Kein gemeinsamer Snapshot mehr → Dataset löschen, vollständig neu
                        async with AsyncSessionLocal() as db:
                            await _log(db, job_id,
                                       f"  Kein gemeinsamer Snapshot gefunden – vollständige Neuübertragung",
                                       "warning", vm.id)
                        zfs_service.local_destroy_dataset(local_dataset)

                transfer_mode = f"inkrementell von @{prev_snapshot_name}" if prev_snapshot_name else "vollständig"
                async with AsyncSessionLocal() as db:
                    await _log(db, job_id,
                               f"  Übertrage ({transfer_mode}): {dataset}@{snapshot_name} → {local_dataset}",
                               vm_id=vm.id)
                await _emit(job_id, {
                    "overall_progress": vm_progress_base + int((ds_progress_base + 10) * vm_progress_step / 100),
                    "current_vm": vm.name,
                    "vm_index": vm_index + 1,
                    "vm_total": vm_total,
                    "vm_progress": ds_progress_base + 10,
                    "step": f"Übertrage Snapshot: {dataset.split('/')[-1]}",
                })

                async def progress_cb(msg: str):
                    await _emit(job_id, {
                        "current_vm": vm.name,
                        "vm_progress": ds_progress_base + 20,
                        "step": msg,
                        "log": msg,
                        "level": "info",
                    })

                try:
                    size = await zfs_service.paramiko_send_receive(
                        ssh_client=ssh_client,
                        remote_dataset=dataset,
                        snapshot_name=snapshot_name,
                        local_dataset=local_dataset,
                        prev_snapshot_name=prev_snapshot_name,
                        progress_callback=progress_cb,
                    )
                    total_size += size
                except Exception as e:
                    async with AsyncSessionLocal() as db:
                        await _log(db, job_id, f"  Übertragungsfehler: {e}", "error", vm.id)
                    vm_ok = False
                    continue

                # Snapshot in DB speichern
                async with AsyncSessionLocal() as db:
                    snap = StoredSnapshot(
                        vm_id=vm.id,
                        job_vm_id=jvm_id,
                        snapshot_name=snapshot_name,
                        zfs_path=f"{local_dataset}@{snapshot_name}",
                        size_bytes=size,
                    )
                    db.add(snap)
                    await db.commit()

                async with AsyncSessionLocal() as db:
                    await _log(db, job_id, f"  Übertragen: {_fmt_bytes(size)}", vm_id=vm.id)

            # ── VM-Konfiguration sichern ──────────────────────────────────────
            try:
                config_path = proxmox_service.backup_vm_config(
                    ssh_client, vm.vmid, vm.vm_type,
                    settings.vm_config_backup_dir, host.name
                )
                async with AsyncSessionLocal() as db:
                    await _log(db, job_id, f"  VM-Konfiguration gesichert: {config_path}", vm_id=vm.id)
            except Exception as e:
                async with AsyncSessionLocal() as db:
                    await _log(db, job_id, f"  Konfigurationssicherung fehlgeschlagen: {e}", "warning", vm.id)

            # ── Retention anwenden ────────────────────────────────────────────
            try:
                deleted = zfs_service.apply_retention(
                    f"{host.backup_pool}/{vm.vmid}",
                    vm.retention_count,
                    vm.retention_days,
                )
                if deleted:
                    async with AsyncSessionLocal() as db:
                        await _log(db, job_id,
                                   f"  Retention: {len(deleted)} alte Snapshots gelöscht", vm_id=vm.id)
            except Exception as e:
                async with AsyncSessionLocal() as db:
                    await _log(db, job_id, f"  Retention-Fehler: {e}", "warning", vm.id)

            # ── Job-VM abschließen ────────────────────────────────────────────
            async with AsyncSessionLocal() as db:
                final_status = "completed" if vm_ok else "failed"
                await _update_job_vm(db, jvm_id, status=final_status,
                                     snapshot_name=snapshot_name,
                                     size_bytes=total_size,
                                     progress=100, finished_at=datetime.utcnow())
                await db.execute(
                    update(VM).where(VM.id == vm.id).values(last_backup_at=datetime.utcnow())
                )
                await db.commit()

            if not vm_ok:
                overall_success = False

            await _emit(job_id, {
                "overall_progress": vm_progress_base + vm_progress_step,
                "current_vm": vm.name,
                "vm_index": vm_index + 1,
                "vm_total": vm_total,
                "vm_progress": 100,
                "step": f"VM {vm.name} abgeschlossen",
            })

    finally:
        ssh_client.close()

    # ── Schritt 4: WireGuard trennen ─────────────────────────────────────────
    if wg_interface:
        async with AsyncSessionLocal() as db:
            await _log(db, job_id, "Trenne WireGuard VPN...")
        await _emit(job_id, {"overall_progress": 97, "step": "Trenne WireGuard VPN..."})
        _safe_wg_down(wg_interface)

    # ── Job abschließen ───────────────────────────────────────────────────────
    final_status = "completed" if overall_success else "failed"
    async with AsyncSessionLocal() as db:
        await _update_job(db, job_id, status=final_status,
                          progress=100, current_step="Backup abgeschlossen",
                          finished_at=datetime.utcnow())
        await _log(db, job_id, f"Backup-Job abgeschlossen: {final_status}")

    await _emit(job_id, {
        "overall_progress": 100,
        "step": "Backup abgeschlossen",
        "log": f"Backup-Job {final_status}",
        "level": "info" if overall_success else "error",
        "done": True,
    })

    # ── Optionaler Shutdown ───────────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(BackupJob).where(BackupJob.id == job_id))
        job = result.scalar_one_or_none()
        if job and job.shutdown_after:
            await _log(db, job_id, "Fahre Backupserver herunter...")
            await asyncio.sleep(5)
            subprocess.run(["shutdown", "-h", "now"], check=False)


def _safe_wg_down(interface: str) -> None:
    try:
        wireguard_service.interface_down(interface)
    except Exception:
        pass


def _fmt_bytes(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"
