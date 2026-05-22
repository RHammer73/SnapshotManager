from datetime import datetime
from sqlalchemy import (
    Integer, String, Boolean, DateTime, Text, ForeignKey, BigInteger
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Host(Base):
    __tablename__ = "hosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22)
    ssh_user: Mapped[str] = mapped_column(String(50), default="root")
    auth_type: Mapped[str] = mapped_column(String(20), default="password")  # password | ssh_key
    ssh_password: Mapped[str] = mapped_column(String(500), nullable=True)
    ssh_private_key: Mapped[str] = mapped_column(Text, nullable=True)
    proxmox_pool: Mapped[str] = mapped_column(String(100), default="rpool")
    backup_pool: Mapped[str] = mapped_column(String(200), nullable=False)
    wol_mac: Mapped[str] = mapped_column(String(17), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vms: Mapped[list["VM"]] = relationship("VM", back_populates="host", cascade="all, delete-orphan")
    wireguard_configs: Mapped[list["WireguardConfig"]] = relationship("WireguardConfig", back_populates="host", cascade="all, delete-orphan")
    backup_jobs: Mapped[list["BackupJob"]] = relationship("BackupJob", back_populates="host", cascade="all, delete-orphan")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="host", cascade="all, delete-orphan")


class WireguardConfig(Base):
    __tablename__ = "wireguard_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    interface_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    config_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="inactive")  # inactive | active

    host: Mapped["Host"] = relationship("Host", back_populates="wireguard_configs")


class VM(Base):
    __tablename__ = "vms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    vmid: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    vm_type: Mapped[str] = mapped_column(String(10), nullable=False)  # qemu | lxc
    zfs_datasets: Mapped[str] = mapped_column(Text, nullable=True)  # JSON list
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    backup_order: Mapped[int] = mapped_column(Integer, default=0)
    retention_count: Mapped[int] = mapped_column(Integer, default=7)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    last_backup_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    host: Mapped["Host"] = relationship("Host", back_populates="vms")
    job_vms: Mapped[list["BackupJobVM"]] = relationship("BackupJobVM", back_populates="vm")
    stored_snapshots: Mapped[list["StoredSnapshot"]] = relationship("StoredSnapshot", back_populates="vm", cascade="all, delete-orphan")


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(20), default="manual")  # manual | schedule
    schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("schedules.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|completed|failed|cancelled
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str] = mapped_column(String(500), nullable=True)
    shutdown_after: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    host: Mapped["Host"] = relationship("Host", back_populates="backup_jobs")
    job_vms: Mapped[list["BackupJobVM"]] = relationship("BackupJobVM", back_populates="job", cascade="all, delete-orphan")
    logs: Mapped[list["BackupLog"]] = relationship("BackupLog", back_populates="job", cascade="all, delete-orphan")


class BackupJobVM(Base):
    __tablename__ = "backup_job_vms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("backup_jobs.id", ondelete="CASCADE"), nullable=False)
    vm_id: Mapped[int] = mapped_column(Integer, ForeignKey("vms.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_name: Mapped[str] = mapped_column(String(200), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    job: Mapped["BackupJob"] = relationship("BackupJob", back_populates="job_vms")
    vm: Mapped["VM"] = relationship("VM", back_populates="job_vms")
    stored_snapshots: Mapped[list["StoredSnapshot"]] = relationship("StoredSnapshot", back_populates="job_vm")


class BackupLog(Base):
    __tablename__ = "backup_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("backup_jobs.id", ondelete="CASCADE"), nullable=False)
    vm_id: Mapped[int] = mapped_column(Integer, ForeignKey("vms.id", ondelete="SET NULL"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    level: Mapped[str] = mapped_column(String(10), default="info")  # info | warning | error
    message: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped["BackupJob"] = relationship("BackupJob", back_populates="logs")


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    shutdown_after: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    host: Mapped["Host"] = relationship("Host", back_populates="schedules")


class StoredSnapshot(Base):
    __tablename__ = "stored_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vm_id: Mapped[int] = mapped_column(Integer, ForeignKey("vms.id", ondelete="CASCADE"), nullable=False)
    job_vm_id: Mapped[int] = mapped_column(Integer, ForeignKey("backup_job_vms.id", ondelete="SET NULL"), nullable=True)
    snapshot_name: Mapped[str] = mapped_column(String(200), nullable=False)
    zfs_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    vm: Mapped["VM"] = relationship("VM", back_populates="stored_snapshots")
    job_vm: Mapped["BackupJobVM"] = relationship("BackupJobVM", back_populates="stored_snapshots")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=True)
