import hashlib
import json
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field


BASE_URL = "https://preeminent-truffle-0ea26e.netlify.app/"
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "dashboard.db"
templates = Jinja2Templates(directory=str(ROOT / "templates"))
app = FastAPI(title="Supermarket POS Subscription API", version="1.0.0")


class LicenseVerifyRequest(BaseModel):
    store_id: str = Field(min_length=1, max_length=100)
    license_key: str = Field(min_length=1, max_length=200)
    hardware_id: Optional[str] = Field(default=None, max_length=200)


class TelemetryRequest(BaseModel):
    total_daily_sales: float = 0
    total_low_stock_count: int = 0
    last_active_cashier_session: Optional[str] = None
    app_status: str = "online"
    payload: Dict[str, Any] = Field(default_factory=dict)


class ExtendSubscriptionRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=3650)


class SalesSyncRequest(BaseModel):
    sales: list[Dict[str, Any]] = Field(default_factory=list)


def db_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS stores (
                store_id TEXT PRIMARY KEY,
                store_name TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                subscription_end DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active', 'expired', 'blocked')),
                monthly_price REAL NOT NULL DEFAULT 0,
                license_key_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                total_daily_sales REAL NOT NULL DEFAULT 0,
                total_low_stock_count INTEGER NOT NULL DEFAULT 0,
                last_active_cashier_session TEXT,
                app_status TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS app_releases (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                version TEXT NOT NULL,
                download_url TEXT NOT NULL
            );
            INSERT OR IGNORE INTO app_releases(id, version, download_url)
            VALUES (1, '1.2.0',
                    'https://preeminent-truffle-0ea26e.netlify.app/static/updates/app-1.2.0.zip');
            """
        )


def key_hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def store_or_404(connection: sqlite3.Connection, store_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM stores WHERE store_id = ?", (store_id.strip(),)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")
    return row


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, connection: sqlite3.Connection = Depends(db_connection)):
    stores = [dict(row) for row in connection.execute(
        "SELECT * FROM stores ORDER BY subscription_end ASC"
    )]
    today = date.today()
    for store in stores:
        end = date.fromisoformat(store["subscription_end"])
        if store["status"] == "active" and end < today:
            store["status"] = "expired"
        store["status_label"] = {
            "active": "نشط", "expired": "منتهي", "blocked": "موقوف"
        }.get(store["status"], store["status"])
    metrics = {
        "active": sum(s["status"] == "active" for s in stores),
        "mrr": sum(s["monthly_price"] for s in stores if s["status"] == "active"),
        "expiring": sum(
            s["status"] == "active"
            and 0 <= (date.fromisoformat(s["subscription_end"]) - today).days <= 30
            for s in stores
        ),
    }
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "stores": stores, "metrics": metrics}
    )


@app.post("/api/v1/license/verify")
def verify_license(
    body: LicenseVerifyRequest,
    connection: sqlite3.Connection = Depends(db_connection),
):
    row = store_or_404(connection, body.store_id)
    status = row["status"]
    if status == "active" and date.fromisoformat(row["subscription_end"]) < date.today():
        status = "expired"
    if not secrets.compare_digest(row["license_key_hash"], key_hash(body.license_key)):
        raise HTTPException(status_code=401, detail="Invalid license key")
    token = hashlib.sha256(
        f"{row['store_id']}:{body.hardware_id or ''}:{row['license_key_hash']}".encode()
    ).hexdigest()
    return {
        "status": status,
        "expires_at": row["subscription_end"],
        "token": token,
    }


@app.post("/api/v1/telemetry/sync")
def sync_telemetry(
    body: TelemetryRequest,
    x_store_id: Optional[str] = Header(default=None),
    connection: sqlite3.Connection = Depends(db_connection),
):
    if not x_store_id:
        raise HTTPException(status_code=400, detail="X-Store-ID header is required")
    store_or_404(connection, x_store_id)
    connection.execute(
        """
        INSERT INTO telemetry (
            store_id, received_at, total_daily_sales, total_low_stock_count,
            last_active_cashier_session, app_status, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            x_store_id.strip(), datetime.utcnow().isoformat(),
            body.total_daily_sales, body.total_low_stock_count,
            body.last_active_cashier_session, body.app_status,
            json.dumps(body.payload, ensure_ascii=False),
        ),
    )
    return {"status": "accepted"}


@app.post("/api/v1/sync/heartbeat")
def sync_heartbeat(
    body: TelemetryRequest,
    x_store_id: Optional[str] = Header(default=None),
    connection: sqlite3.Connection = Depends(db_connection),
):
    return sync_telemetry(body, x_store_id, connection)


@app.post("/api/v1/sync/sales")
def sync_sales(
    body: SalesSyncRequest,
    x_store_id: Optional[str] = Header(default=None),
    connection: sqlite3.Connection = Depends(db_connection),
):
    if not x_store_id:
        raise HTTPException(status_code=400, detail="X-Store-ID header is required")
    store_or_404(connection, x_store_id)
    sales = body.sales
    total = 0.0
    for index, sale in enumerate(sales):
        raw_total = sale.get("total", 0)
        try:
            total += float(raw_total or 0)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"sales[{index}].total must be a number",
            ) from exc
    connection.execute(
        """
        INSERT INTO telemetry (
            store_id, received_at, total_daily_sales, total_low_stock_count,
            last_active_cashier_session, app_status, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            x_store_id.strip(), datetime.utcnow().isoformat(),
            total, 0, None, "sales_sync",
            json.dumps(body.dict(), ensure_ascii=False),
        ),
    )
    return {"status": "accepted", "received": len(sales)}


@app.get("/api/v1/app/check-update")
def check_update(connection: sqlite3.Connection = Depends(db_connection)):
    row = connection.execute(
        "SELECT version, download_url FROM app_releases WHERE id = 1"
    ).fetchone()
    return {"version": row["version"], "download_url": row["download_url"]}


@app.post("/api/v1/stores/{store_id}/extend")
def extend_subscription(
    store_id: str,
    body: ExtendSubscriptionRequest,
    connection: sqlite3.Connection = Depends(db_connection),
):
    row = store_or_404(connection, store_id)
    current_end = max(date.today(), date.fromisoformat(row["subscription_end"]))
    new_end = current_end + timedelta(days=body.days)
    connection.execute(
        "UPDATE stores SET subscription_end = ?, status = 'active' WHERE store_id = ?",
        (new_end.isoformat(), store_id.strip()),
    )
    return {"store_id": store_id, "subscription_end": new_end.isoformat(), "status": "active"}


@app.post("/api/v1/stores/{store_id}/block")
def block_store(
    store_id: str,
    connection: sqlite3.Connection = Depends(db_connection),
):
    store_or_404(connection, store_id)
    connection.execute("UPDATE stores SET status = 'blocked' WHERE store_id = ?", (store_id.strip(),))
    return {"store_id": store_id, "status": "blocked"}


@app.post("/api/v1/stores/{store_id}/generate-license")
def generate_license(
    store_id: str,
    connection: sqlite3.Connection = Depends(db_connection),
):
    store_or_404(connection, store_id)
    license_key = f"POS-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    connection.execute(
        "UPDATE stores SET license_key_hash = ? WHERE store_id = ?",
        (key_hash(license_key), store_id.strip()),
    )
    return {"store_id": store_id, "license_key": license_key}


@app.get("/api/v1/app/version")
def version_compatibility(
    store_id: str = Query(..., min_length=1),
    connection: sqlite3.Connection = Depends(db_connection),
):
    # Compatibility endpoint for older desktop builds.
    store_or_404(connection, store_id)
    release = check_update(connection)
    return {
        "latest_version": release["version"],
        "download_url": release["download_url"],
    }
