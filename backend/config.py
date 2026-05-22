from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    app_name: str = "SnapshotManager"
    app_version: str = "1.0.0"
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/snapshotmanager.db"
    wireguard_dir: str = "/etc/wireguard"
    vm_config_backup_dir: str = "/var/lib/snapshotmanager/vm-configs"
    frontend_dist: str = str(BASE_DIR.parent / "frontend" / "dist")

    class Config:
        env_file = ".env"


settings = Settings()

