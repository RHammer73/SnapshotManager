import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from database import init_db
from routers import hosts, vms, jobs, schedules, wireguard, snapshots
from routers.settings import router as settings_router
from services import scheduler_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SnapshotManager startet...")
    await init_db()
    os.makedirs(settings.vm_config_backup_dir, exist_ok=True)

    scheduler_service.start_scheduler()
    await scheduler_service.load_schedules()
    logger.info("Scheduler gestartet")

    yield

    scheduler_service.stop_scheduler()
    logger.info("SnapshotManager beendet")


app = FastAPI(
    title="SnapshotManager",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API-Router einbinden
app.include_router(hosts.router)
app.include_router(vms.router)
app.include_router(jobs.router)
app.include_router(schedules.router)
app.include_router(wireguard.router)
app.include_router(snapshots.router)
app.include_router(settings_router)


# Frontend-Static-Files ausliefern (nach dem Build)
frontend_dist = settings.frontend_dist
if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index = os.path.join(frontend_dist, "index.html")
        return FileResponse(index)
else:
    @app.get("/")
    async def root():
        return {"message": "SnapshotManager API läuft. Frontend noch nicht gebaut."}
