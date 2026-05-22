"""WireGuard-Verwaltung: Configs schreiben, Interfaces up/down."""
import subprocess
import os
from config import settings


def _wg_config_path(interface_name: str) -> str:
    return os.path.join(settings.wireguard_dir, f"{interface_name}.conf")


def write_config(interface_name: str, config_content: str) -> None:
    os.makedirs(settings.wireguard_dir, exist_ok=True)
    path = _wg_config_path(interface_name)
    with open(path, "w") as f:
        f.write(config_content)
    os.chmod(path, 0o600)


def remove_config(interface_name: str) -> None:
    path = _wg_config_path(interface_name)
    if os.path.exists(path):
        os.remove(path)


def interface_up(interface_name: str) -> None:
    write_config_if_missing(interface_name)
    result = subprocess.run(
        ["wg-quick", "up", interface_name],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"wg-quick up fehlgeschlagen: {result.stderr}")


def write_config_if_missing(interface_name: str) -> None:
    path = _wg_config_path(interface_name)
    if not os.path.exists(path):
        raise RuntimeError(f"WireGuard-Konfiguration nicht gefunden: {path}")


def interface_down(interface_name: str) -> None:
    result = subprocess.run(
        ["wg-quick", "down", interface_name],
        capture_output=True, text=True, timeout=30
    )
    # Ignoriere Fehler wenn Interface bereits inaktiv ist
    if result.returncode != 0 and "is not a WireGuard interface" not in result.stderr:
        if "No such device" not in result.stderr and "Cannot find device" not in result.stderr:
            raise RuntimeError(f"wg-quick down fehlgeschlagen: {result.stderr}")


def get_status(interface_name: str) -> dict:
    result = subprocess.run(
        ["wg", "show", interface_name],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return {"active": False, "peers": []}

    lines = result.stdout.splitlines()
    peers = []
    current_peer = None
    for line in lines:
        line = line.strip()
        if line.startswith("peer:"):
            if current_peer:
                peers.append(current_peer)
            current_peer = {"public_key": line.split(": ", 1)[1].strip()}
        elif line.startswith("endpoint:") and current_peer:
            current_peer["endpoint"] = line.split(": ", 1)[1].strip()
        elif line.startswith("latest handshake:") and current_peer:
            current_peer["last_handshake"] = line.split(": ", 1)[1].strip()
    if current_peer:
        peers.append(current_peer)

    return {"active": True, "peers": peers, "raw": result.stdout}


def is_active(interface_name: str) -> bool:
    result = subprocess.run(
        ["wg", "show", interface_name],
        capture_output=True, text=True, timeout=10
    )
    return result.returncode == 0
