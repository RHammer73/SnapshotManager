"""Proxmox-Host-Zugriff via SSH: VM-Discovery und Konfigurationssicherung."""
import io
import json
import os
import re
from typing import Optional
import paramiko
from config import settings


def get_ssh_client(
    ip: str,
    port: int,
    user: str,
    auth_type: str,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if auth_type == "ssh_key" and private_key:
        try:
            key = paramiko.RSAKey.from_private_key(io.StringIO(private_key))
        except Exception:
            try:
                key = paramiko.Ed25519Key.from_private_key(io.StringIO(private_key))
            except Exception:
                key = paramiko.ECDSAKey.from_private_key(io.StringIO(private_key))
        client.connect(ip, port=port, username=user, pkey=key, timeout=15)
    else:
        client.connect(ip, port=port, username=user, password=password, timeout=15)

    return client


def _exec(client: paramiko.SSHClient, cmd: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, stdout.read().decode(errors="replace"), stderr.read().decode(errors="replace")


def discover_vms(client: paramiko.SSHClient, zfs_pool: str) -> list[dict]:
    """
    Liest alle VMs und Container auf dem Proxmox-Host via SSH aus.
    Gibt Liste mit vm-Informationen zurück.
    """
    vms = []

    # QEMU VMs aus Konfigurationsverzeichnis
    rc, out, _ = _exec(client, "ls /etc/pve/qemu-server/ 2>/dev/null")
    if rc == 0:
        for conf_file in out.strip().splitlines():
            conf_file = conf_file.strip()
            if not conf_file.endswith(".conf"):
                continue
            vmid_str = conf_file.replace(".conf", "")
            if not vmid_str.isdigit():
                continue
            vmid = int(vmid_str)
            rc2, conf, _ = _exec(client, f"cat /etc/pve/qemu-server/{conf_file}")
            name = f"vm-{vmid}"
            for line in conf.splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                    break

            datasets = _find_vm_datasets(client, zfs_pool, vmid, "qemu")
            vms.append({
                "vmid": vmid,
                "name": name,
                "vm_type": "qemu",
                "zfs_datasets": json.dumps(datasets),
            })

    # LXC Container
    rc, out, _ = _exec(client, "ls /etc/pve/lxc/ 2>/dev/null")
    if rc == 0:
        for conf_file in out.strip().splitlines():
            conf_file = conf_file.strip()
            if not conf_file.endswith(".conf"):
                continue
            vmid_str = conf_file.replace(".conf", "")
            if not vmid_str.isdigit():
                continue
            vmid = int(vmid_str)
            rc2, conf, _ = _exec(client, f"cat /etc/pve/lxc/{conf_file}")
            name = f"ct-{vmid}"
            for line in conf.splitlines():
                if line.startswith("hostname:"):
                    name = line.split(":", 1)[1].strip()
                    break

            datasets = _find_vm_datasets(client, zfs_pool, vmid, "lxc")
            vms.append({
                "vmid": vmid,
                "name": name,
                "vm_type": "lxc",
                "zfs_datasets": json.dumps(datasets),
            })

    vms.sort(key=lambda v: v["vmid"])
    return vms


def _find_vm_datasets(
    client: paramiko.SSHClient, pool: str, vmid: int, vm_type: str
) -> list[str]:
    """Findet ZFS-Datasets für eine VM via 'zfs list'."""
    if vm_type == "lxc":
        patterns = [f"{pool}/data/subvol-{vmid}-", f"{pool}/subvol-{vmid}-"]
    else:
        patterns = [f"{pool}/data/vm-{vmid}-", f"{pool}/vm-{vmid}-"]

    rc, out, _ = _exec(client, f"zfs list -H -o name -r {pool}")
    datasets = []
    if rc == 0:
        for line in out.strip().splitlines():
            line = line.strip()
            for pattern in patterns:
                if line.startswith(pattern):
                    datasets.append(line)
                    break

    # Fallback: Suche nach vmid im Dataset-Namen
    if not datasets:
        rc, out, _ = _exec(
            client,
            f"zfs list -H -o name -r {pool} | grep -E '[-/]{vmid}[-@]|[-/]{vmid}$'"
        )
        if rc == 0:
            datasets = [l.strip() for l in out.strip().splitlines() if l.strip()]

    return datasets


def backup_vm_config(
    client: paramiko.SSHClient,
    vmid: int,
    vm_type: str,
    backup_dir: str,
    host_name: str,
) -> str:
    """
    Kopiert die VM-Konfigurationsdatei auf den Backupserver.
    Gibt den lokalen Pfad zurück.
    """
    if vm_type == "qemu":
        remote_path = f"/etc/pve/qemu-server/{vmid}.conf"
    else:
        remote_path = f"/etc/pve/lxc/{vmid}.conf"

    rc, content, _ = _exec(client, f"cat {remote_path}")
    if rc != 0 or not content:
        raise RuntimeError(f"VM-Config nicht lesbar: {remote_path}")

    local_dir = os.path.join(backup_dir, host_name)
    os.makedirs(local_dir, exist_ok=True)

    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    local_file = os.path.join(local_dir, f"{vmid}-{vm_type}-{timestamp}.conf")
    with open(local_file, "w") as f:
        f.write(content)

    return local_file


def test_connection(
    ip: str,
    port: int,
    user: str,
    auth_type: str,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
) -> dict:
    """Testet die SSH-Verbindung und gibt Systeminformationen zurück."""
    try:
        client = get_ssh_client(ip, port, user, auth_type, password, private_key)
        rc, out, _ = _exec(client, "uname -n && uname -r && zfs version 2>/dev/null | head -1")
        client.close()
        return {"success": True, "info": out.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}
