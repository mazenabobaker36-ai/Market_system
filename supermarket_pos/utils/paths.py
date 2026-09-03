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
    In frozen/packaged mode on Windows, this is %LOCALAPPDATA%/SupermarketPOS.
    In development mode, this points to the supermarket_pos project root.
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                path = Path(local_appdata) / "SupermarketPOS"
                path.mkdir(parents=True, exist_ok=True)
                return path
        else:
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                path = Path(xdg_data) / "supermarket_pos"
            else:
                path = Path.home() / ".local" / "share" / "supermarket_pos"
            path.mkdir(parents=True, exist_ok=True)
            return path
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


APP_DIR: Path = get_app_dir()
DATA_DIR: Path = get_data_dir()

# Persistent paths
DB_PATH: Path = DATA_DIR / "pos_database.db"
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
    PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Seed database initialization for first run when frozen
    if getattr(sys, "frozen", False) and not DB_PATH.exists():
        seed_db = APP_DIR / "pos_database.db"
        if seed_db.exists():
            try:
                shutil.copy2(seed_db, DB_PATH)
            except Exception:
                pass

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
