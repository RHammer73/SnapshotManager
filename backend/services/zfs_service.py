"""ZFS-Operationen auf dem Backupserver (lokal) und via SSH auf Proxmox."""
import os
import subprocess
import json
import asyncio
from datetime import datetime
from typing import Optional
import paramiko


def _run_local(cmd: list[str], timeout: int = 300) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def local_dataset_exists(dataset: str) -> bool:
    rc, _, _ = _run_local(["zfs", "list", "-H", "-o", "name", dataset])
    return rc == 0


def local_create_dataset(dataset: str) -> None:
    rc, _, err = _run_local(["zfs", "create", "-p", dataset])
    if rc != 0:
        raise RuntimeError(f"zfs create fehlgeschlagen: {err}")


def local_list_snapshots(dataset: str) -> list[dict]:
    rc, out, _ = _run_local([
        "zfs", "list", "-t", "snapshot", "-H", "-o", "name,creation,used",
        "-r", dataset
    ])
    if rc != 0:
        return []
    snapshots = []
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            snapshots.append({"name": parts[0], "creation": parts[1], "used": parts[2]})
    return snapshots


def local_destroy_snapshot(snapshot_path: str) -> None:
    rc, _, err = _run_local(["zfs", "destroy", snapshot_path])
    if rc != 0:
        raise RuntimeError(f"zfs destroy fehlgeschlagen: {err}")


def local_destroy_dataset(dataset: str) -> None:
    """Zerstört ein lokales ZFS-Dataset inklusive aller Snapshots."""
    rc, _, err = _run_local(["zfs", "destroy", "-r", dataset])
    if rc != 0:
        raise RuntimeError(f"zfs destroy -r fehlgeschlagen: {err}")


def local_get_latest_snapshot(dataset: str) -> Optional[str]:
    """Gibt den Snapshot-Namen (ohne Dataset@-Prefix) des neuesten lokalen Snapshots zurück."""
    snapshots = local_list_snapshots(dataset)
    if not snapshots:
        return None
    snapshots.sort(key=lambda s: s["name"])
    return snapshots[-1]["name"].split("@")[-1]


def local_get_dataset_size(dataset: str) -> int:
    """Gibt die verwendete Größe des Datasets in Bytes zurück."""
    rc, out, _ = _run_local(["zfs", "list", "-H", "-o", "used", "-p", dataset])
    if rc != 0:
        return 0
    try:
        return int(out.strip())
    except ValueError:
        return 0


async def ssh_create_snapshot(ssh: paramiko.SSHClient, dataset: str, snapshot_name: str) -> None:
    full_name = f"{dataset}@{snapshot_name}"
    stdin, stdout, stderr = ssh.exec_command(f"zfs snapshot {full_name}")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        err = stderr.read().decode()
        raise RuntimeError(f"zfs snapshot fehlgeschlagen ({full_name}): {err}")


async def ssh_list_snapshots(ssh: paramiko.SSHClient, dataset: str) -> list[str]:
    cmd = f"zfs list -t snapshot -H -o name -r {dataset}"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.channel.recv_exit_status()
    return [line.strip() for line in stdout.read().decode().splitlines() if line.strip()]


async def ssh_destroy_snapshot(ssh: paramiko.SSHClient, snapshot: str) -> None:
    stdin, stdout, stderr = ssh.exec_command(f"zfs destroy {snapshot}")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        err = stderr.read().decode()
        raise RuntimeError(f"zfs destroy fehlgeschlagen: {err}")


async def ssh_snapshot_exists(ssh: paramiko.SSHClient, snapshot: str) -> bool:
    """Prüft ob ein Snapshot auf dem Remote-Host existiert."""
    stdin, stdout, stderr = ssh.exec_command(
        f"zfs list -t snapshot -H -o name {snapshot}"
    )
    exit_code = stdout.channel.recv_exit_status()
    return exit_code == 0


def _paramiko_send_receive_sync(
    ssh_client: paramiko.SSHClient,
    snapshot_full: str,
    local_dataset: str,
    prev_snapshot_name: Optional[str] = None,
) -> None:
    """
    ZFS-Übertragung via bestehender Paramiko-Verbindung (OpenZFS).
    Inkrementeller Send (-i) wenn prev_snapshot_name angegeben, sonst vollständig.
    """
    channel = ssh_client.get_transport().open_session()

    if prev_snapshot_name:
        remote_dataset = snapshot_full.split("@")[0]
        prev_full = f"{remote_dataset}@{prev_snapshot_name}"
        send_cmd = f"zfs send -p -i {prev_full} {snapshot_full}"
    else:
        send_cmd = f"zfs send -p {snapshot_full}"

    channel.exec_command(send_cmd)

    recv_proc = subprocess.Popen(
        ["zfs", "receive", "-F", "-u", local_dataset],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        while True:
            # Frühzeitigen Exit von zfs receive erkennen bevor geschrieben wird
            if recv_proc.poll() is not None:
                break
            data = channel.recv(256 * 1024)
            if not data:
                break
            try:
                recv_proc.stdin.write(data)
            except BrokenPipeError:
                break
    finally:
        try:
            recv_proc.stdin.close()
        except Exception:
            pass

    recv_proc.wait()
    send_exit = channel.recv_exit_status()

    recv_err = recv_proc.stderr.read().decode(errors="replace").strip()
    send_err = ""
    while channel.recv_stderr_ready():
        send_err += channel.recv_stderr(65536).decode(errors="replace")
    send_err = send_err.strip()

    if recv_proc.returncode != 0:
        raise RuntimeError(f"zfs receive fehlgeschlagen: {recv_err}")
    if send_exit != 0:
        raise RuntimeError(f"zfs send fehlgeschlagen (rc={send_exit}): {send_err}")


async def paramiko_send_receive(
    ssh_client: paramiko.SSHClient,
    remote_dataset: str,
    snapshot_name: str,
    local_dataset: str,
    prev_snapshot_name: Optional[str] = None,
    progress_callback=None,
) -> int:
    """
    Streamt zfs send von Proxmox via Paramiko nach lokal via zfs receive.
    Inkrementell wenn prev_snapshot_name gesetzt, sonst vollständig.
    Gibt übertragene Bytes zurück.
    """
    snapshot_full = f"{remote_dataset}@{snapshot_name}"

    if progress_callback:
        mode = f"inkrementell von @{prev_snapshot_name}" if prev_snapshot_name else "vollständig"
        await progress_callback(f"Übertrage {snapshot_full} ({mode}) ...")

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, _paramiko_send_receive_sync,
        ssh_client, snapshot_full, local_dataset, prev_snapshot_name,
    )

    return local_get_dataset_size(local_dataset)


def apply_retention(backup_pool_dataset: str, retention_count: int, retention_days: int) -> list[str]:
    """
    Löscht alte Snapshots gemäß Aufbewahrungsregeln.
    Gibt Liste der gelöschten Snapshot-Namen zurück.
    """
    snapshots = local_list_snapshots(backup_pool_dataset)
    deleted = []

    # Snapshots nach Name sortieren (Name enthält Timestamp)
    snapshots.sort(key=lambda s: s["name"])

    # Retention nach Anzahl
    if retention_count > 0 and len(snapshots) > retention_count:
        to_delete = snapshots[:len(snapshots) - retention_count]
        for snap in to_delete:
            try:
                local_destroy_snapshot(snap["name"])
                deleted.append(snap["name"])
            except Exception:
                pass

    # Retention nach Alter (Tage) — Snapshots mit Timestamp im Namen
    if retention_days > 0:
        cutoff = datetime.utcnow().timestamp() - (retention_days * 86400)
        remaining = local_list_snapshots(backup_pool_dataset)
        for snap in remaining:
            snap_name = snap["name"].split("@")[-1]
            # Format: backup-YYYYMMDD-HHMMSS
            try:
                snap_dt = datetime.strptime(snap_name, "backup-%Y%m%d-%H%M%S")
                if snap_dt.timestamp() < cutoff:
                    local_destroy_snapshot(snap["name"])
                    deleted.append(snap["name"])
            except ValueError:
                pass

    return deleted
