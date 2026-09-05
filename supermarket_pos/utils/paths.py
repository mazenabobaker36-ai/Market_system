import os
import shutil
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """
    Returns the read-only application directory containing bundled assets.
    In frozen/packaged mode, this points to sys._MEIPASS or the executable folder.
    In development mode, this points to the supermarket_pos project root.
    """
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    """
    Returns the persistent user data directory where writable files (database,
    product images, generated labels, invoice PDFs) must be stored.
    Uses a dedicated writable AppData/Data directory in every environment.
    """
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return root / "MySupermarketPOS" / "Data"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "MySupermarketPOS" / "Data"


def resolve_database_path(app_name: str = "MySupermarketPOS") -> Path:
    """Resolve and create the persistent database directory without touching app files."""
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    data_dir = root / app_name / "Data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "supermarket.db"


APP_DIR: Path = get_app_dir()
DATA_DIR: Path = get_data_dir()

# Persistent paths
DB_PATH: Path = resolve_database_path()
PRODUCT_IMAGES_DIR: Path = DATA_DIR / "assets" / "product_images"
LABELS_DIR: Path = DATA_DIR / "assets" / "labels"
REPORTS_DIR: Path = DATA_DIR / "reports"

# Bundled read-only assets
TEMPLATE_PATH: Path = APP_DIR / "assets" / "invoice_template.html"


def ensure_data_dirs() -> None:
    """
    Ensures all persistent folders exist.
    If the application is running packaged and pos_database.db does not exist yet
    in DATA_DIR, copies the bundled seed database from APP_DIR.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Seed database initialization for first run when frozen
    if not DB_PATH.exists():
        candidates = [
            DATA_DIR / "pos_database.db",
            APP_DIR / "supermarket.db",
            APP_DIR / "pos_database.db",
        ]
        for seed_db in candidates:
            if seed_db.exists():
                try:
                    shutil.copy2(seed_db, DB_PATH)
                except OSError:
                    pass
                break

        # Also copy bundled sample product images if any
        bundled_images = APP_DIR / "assets" / "product_images"
        if bundled_images.exists():
            for item in bundled_images.glob("*"):
                target = PRODUCT_IMAGES_DIR / item.name
                if not target.exists():
                    try:
                        shutil.copy2(item, target)
                    except Exception:
                        pass
