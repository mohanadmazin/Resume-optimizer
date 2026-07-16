"""Application paths — user data directory, database, logs, exports."""
from pathlib import Path


USER_DATA_DIR = Path.home() / ".resume_optimizer"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = USER_DATA_DIR / "resume_optimizer.db"

CONFIG_PATH = USER_DATA_DIR / "settings.json"

LOG_DIR = USER_DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

BACKUP_DIR = USER_DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

EXPORT_DIR = USER_DATA_DIR / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

CACHE_DIR = USER_DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
