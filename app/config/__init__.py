from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent


DATA_DIR = APP_DIR / "data"

DATA_DIR.mkdir(
    exist_ok=True
)


DB_PATH = DATA_DIR / "resume_optimizer.db"
from .config_manager import (
    load_config,
    save_config,
    DEFAULT_CONFIG,
)

from pathlib import Path


APP_DIR = Path(__file__).parent.parent

DATA_DIR = APP_DIR / "data"

DB_PATH = DATA_DIR / "resume_optimizer.db"