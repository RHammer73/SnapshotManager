from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Host ──────────────────────────────────────────────────────────────────────

class HostBase(BaseModel):
    name: str
    description: Optional[str] = None
    ip_address: str
    ssh_port: int = 22
    ssh_user: str = "root"
    auth_type: str = "password"
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    proxmox_pool: str = "rpool"
    backup_pool: str
    wol_mac: Optional[str] = None


class HostCreate(HostBase):
    pass


class HostUpdate(HostBase):
    pass


class HostRead(HostBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HostReadSafe(BaseModel):
    """Host ohne sensible Felder"""
    id: int
    name: str
    description: Optional[str]
    ip_address: str
    ssh_port: int
    ssh_user: str
    auth_type: str
    proxmox_pool: str
    backup_pool: str
    wol_mac: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── WireGuard ─────────────────────────────────────────────────────────────────

class WireguardBase(BaseModel):
    host_id: int
    interface_name: str
    config_content: str


class WireguardCreate(WireguardBase):
    pass


class WireguardUpdate(BaseModel):
    interface_name: Optional[str] = None
    config_content: Optional[str] = None


class WireguardRead(WireguardBase):
    id: int
    status: str

    class Config:
        from_attributes = True


# ── VM ────────────────────────────────────────────────────────────────────────

class VMBase(BaseModel):
    enabled: bool = True
    backup_order: int = 0
    retention_count: int = 7
    retention_days: int = 30


class VMUpdate(VMBase):
    pass


class VMReorderItem(BaseModel):
    id: int
    backup_order: int


class VMRead(BaseModel):
    id: int
    host_id: int
    vmid: int
    name: str
    vm_type: str
    zfs_datasets: Optional[str]
    enabled: bool
    backup_order: int
    retention_count: int
    retention_days: int
    last_backup_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── BackupJob ─────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    host_id: int
    shutdown_after: bool = False


class JobVMRead(BaseModel):
    id: int
    vm_id: int
    status: str
    progress: int
    snapshot_name: Optional[str]
    size_bytes: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class JobRead(BaseModel):
    id: int
    host_id: int
    triggered_by: str
    schedule_id: Optional[int]
    status: str
    progress: int
    current_step: Optional[str]
    shutdown_after: bool
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    job_vms: List[JobVMRead] = []

    class Config:
        from_attributes = True


class JobLogRead(BaseModel):
    id: int
    job_id: int
    vm_id: Optional[int]
    timestamp: datetime
    level: str
    message: str

    class Config:
        from_attributes = True


# ── Schedule ──────────────────────────────────────────────────────────────────

class ScheduleBase(BaseModel):
    host_id: int
    name: str
    cron_expression: str
    enabled: bool = True
    shutdown_after: bool = False


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    shutdown_after: Optional[bool] = None


class ScheduleRead(ScheduleBase):
    id: int
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── StoredSnapshot ────────────────────────────────────────────────────────────

class SnapshotRead(BaseModel):
    id: int
    vm_id: int
    job_vm_id: Optional[int]
    snapshot_name: str
    zfs_path: str
    created_at: datetime
    size_bytes: int

    class Config:
        from_attributes = True


# ── AppSettings ───────────────────────────────────────────────────────────────

class SettingRead(BaseModel):
    key: str
    value: Optional[str]

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    settings: dict[str, str]


# ── Progress Event (SSE) ──────────────────────────────────────────────────────

class ProgressEvent(BaseModel):
    overall_progress: int = 0
    current_vm: Optional[str] = None
    vm_index: int = 0
    vm_total: int = 0
    vm_progress: int = 0
    step: str = ""
    log: Optional[str] = None
    level: str = "info"
    done: bool = False
    error: Optional[str] = None
