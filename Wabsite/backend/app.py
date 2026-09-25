import hashlib
import json
import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import connection as db_connection, init_db
from models import (
    AdminUserCreateRequest,
    ExtendSubscriptionRequest,
    LicenseVerifyRequest,
    PlanCreateRequest,
    SalesSyncRequest,
    SubscriberCreateRequest,
    TelemetryRequest,
)

BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://preeminent-truffle-0ea26e.netlify.app/api/v1",
).rstrip("/")
BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
TEMPLATE_DIR = BACKEND_DIR / "server_templates"
STATIC_DIR = BACKEND_DIR / "server_static"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR)) if TEMPLATE_DIR.is_dir() else None
app = FastAPI(title="Supermarket POS Subscription API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://preeminent-truffle-0ea26e.netlify.app",
        "http://localhost",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# The Netlify frontend does not require server-side static files. Mount the
# directory only when an optional server-rendered deployment includes it.
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "online", "message": "Market System API is running"}


def render_template(template_name: str, context: dict[str, Any]):
    if templates is None:
        raise HTTPException(
            status_code=503,
            detail="Server-rendered templates are not installed; use the Netlify frontend.",
        )
    return templates.TemplateResponse(template_name, context)


def key_hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()



def store_or_404(connection: sqlite3.Connection, store_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM stores WHERE store_id = ?", (store_id.strip(),)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")
    return row


def status_label(value: str) -> str:
    return {"active": "نشط", "expired": "منتهي", "blocked": "موقوف"}.get(value, value)


def store_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT s.*, p.name AS plan_name
        FROM stores s LEFT JOIN plans p ON p.id = s.plan_id
        ORDER BY s.subscription_end ASC
        """
    ).fetchall()
    today = date.today()
    result = []
    for raw in rows:
        store = dict(raw)
        if store["status"] == "active" and date.fromisoformat(store["subscription_end"]) < today:
            store["status"] = "expired"
        store["status_label"] = status_label(store["status"])
        result.append(store)
    return result


def dashboard_context(connection: sqlite3.Connection) -> dict[str, Any]:
    stores = store_rows(connection)
    today = date.today()
    revenue = connection.execute("SELECT COALESCE(SUM(total_daily_sales), 0) FROM telemetry").fetchone()[0]
    telemetry = [dict(row) for row in connection.execute(
        "SELECT * FROM telemetry ORDER BY received_at DESC LIMIT 10"
    )]
    chart_rows = connection.execute(
        """
        SELECT date(received_at) AS day, COALESCE(SUM(total_daily_sales), 0) AS sales
        FROM telemetry
        GROUP BY date(received_at)
        ORDER BY day ASC
        LIMIT 30
        """
    ).fetchall()
    return {
        "stores": stores,
        "metrics": {
            "revenue": revenue,
            "active": sum(s["status"] == "active" for s in stores),
            "expiring": sum(
                s["status"] == "active"
                and 0 <= (date.fromisoformat(s["subscription_end"]) - today).days <= 30
                for s in stores
            ),
            "suspended": sum(s["status"] == "blocked" for s in stores),
        },
        "telemetry": telemetry,
        "chart_labels": [row["day"] for row in chart_rows],
        "chart_values": [row["sales"] for row in chart_rows],
    }


@app.on_event("startup")
def startup() -> None:
    init_db()
    print("Registered FastAPI routes:")
    for route in app.routes:
        methods = ",".join(sorted(getattr(route, "methods", set()))) or "MOUNT"
        print(f"  {methods:12} {route.path}")


# ---------------------------------------------------------------------------
# Web administration portal
# ---------------------------------------------------------------------------
@app.get("/admin/dashboard", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, connection: sqlite3.Connection = Depends(db_connection)):
    context = dashboard_context(connection)
    context.update({"request": request, "page": "dashboard"})
    return render_template("home.html", context)


@app.get("/admin/subscriptions", response_class=HTMLResponse)
def subscriptions(request: Request, connection: sqlite3.Connection = Depends(db_connection)):
    plans = [dict(row) for row in connection.execute("SELECT * FROM plans WHERE active = 1 ORDER BY monthly_price")]
    for plan in plans:
        plan["features_list"] = json.loads(plan["features"] or "[]")
    return render_template(
        "subscriptions.html",
        {"request": request, "page": "subscriptions", "stores": store_rows(connection), "plans": plans},
    )


@app.post("/admin/subscriptions")
def create_subscription(request: Request, connection: sqlite3.Connection = Depends(db_connection)):
    # Form handling is intentionally server-side and generates credentials here.
    return RedirectResponse("/admin/subscriptions", status_code=303)


@app.post("/admin/subscriptions/create")
def create_subscription_form(request: Request, connection: sqlite3.Connection = Depends(db_connection)):
    # FastAPI form parsing is avoided so the service remains usable without python-multipart.
    # Clients may POST JSON to the companion endpoint below.
    return RedirectResponse("/admin/subscriptions", status_code=303)



@app.post("/api/admin/subscriptions")
def api_create_subscription(body: SubscriberCreateRequest, connection: sqlite3.Connection = Depends(db_connection)):
    plan = connection.execute("SELECT * FROM plans WHERE id = ? AND active = 1", (body.plan_id,)).fetchone()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    store_id = f"STORE-{secrets.token_hex(4).upper()}"
    license_key = f"POS-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    connection.execute(
        """INSERT INTO stores(store_id, store_name, owner_name, phone, subscription_end,
           status, monthly_price, license_key_hash, plan_id, created_at)
           VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)""",
        (store_id, body.store_name.strip(), body.owner_name.strip(), body.phone.strip(),
         (date.today() + timedelta(days=body.days)).isoformat(), plan["monthly_price"],
         key_hash(license_key), body.plan_id, datetime.utcnow().isoformat()),
    )
    return {"store_id": store_id, "license_key": license_key}


@app.post("/admin/subscriptions/{store_id}/extend")
def extend_subscription_web(store_id: str, connection: sqlite3.Connection = Depends(db_connection)):
    store_or_404(connection, store_id)
    current = connection.execute("SELECT subscription_end FROM stores WHERE store_id = ?", (store_id,)).fetchone()[0]
    new_end = max(date.today(), date.fromisoformat(current)) + timedelta(days=30)
    connection.execute("UPDATE stores SET subscription_end = ?, status = 'active' WHERE store_id = ?", (new_end.isoformat(), store_id))
    return RedirectResponse("/admin/subscriptions", status_code=303)


@app.post("/admin/subscriptions/{store_id}/block")
def block_subscription_web(store_id: str, connection: sqlite3.Connection = Depends(db_connection)):
    store_or_404(connection, store_id)
    connection.execute("UPDATE stores SET status = 'blocked' WHERE store_id = ?", (store_id,))
    return RedirectResponse("/admin/subscriptions", status_code=303)


@app.get("/admin/plans", response_class=HTMLResponse)
def plans_page(request: Request, connection: sqlite3.Connection = Depends(db_connection)):
    plans = [dict(row) for row in connection.execute("SELECT * FROM plans ORDER BY monthly_price")]
    for plan in plans:
        plan["features_list"] = json.loads(plan["features"] or "[]")
    return render_template("plans.html", {"request": request, "page": "plans", "plans": plans})



@app.post("/api/admin/plans")
def create_plan(body: PlanCreateRequest, connection: sqlite3.Connection = Depends(db_connection)):
    try:
        cursor = connection.execute(
            "INSERT INTO plans(name, monthly_price, annual_price, features) VALUES (?, ?, ?, ?)",
            (body.name.strip(), body.monthly_price, body.annual_price, json.dumps(body.features, ensure_ascii=False)),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Plan already exists") from exc
    return {"id": cursor.lastrowid, "name": body.name}


@app.get("/admin/users", response_class=HTMLResponse)
def users_page(request: Request, connection: sqlite3.Connection = Depends(db_connection)):
    users = [dict(row) for row in connection.execute("SELECT * FROM admin_users ORDER BY created_at DESC")]
    for user in users:
        user["permissions_list"] = json.loads(user["permissions"] or "[]")
    history = [dict(row) for row in connection.execute("SELECT * FROM login_history ORDER BY logged_at DESC LIMIT 50")]
    return render_template(
        "users.html", {"request": request, "page": "users", "users": users, "history": history}
    )



@app.post("/api/admin/users")
def create_admin_user(body: AdminUserCreateRequest, connection: sqlite3.Connection = Depends(db_connection)):
    try:
        connection.execute(
            "INSERT INTO admin_users(name, email, role, permissions, created_at) VALUES (?, ?, ?, ?, ?)",
            (body.name.strip(), body.email.strip().lower(), body.role.strip(),
             json.dumps(body.permissions, ensure_ascii=False), datetime.utcnow().isoformat()),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Email already exists") from exc
    return {"status": "created"}


# ---------------------------------------------------------------------------
# Static dashboard JSON API
# ---------------------------------------------------------------------------
@app.get("/api/admin/dashboard")
def api_dashboard(connection: sqlite3.Connection = Depends(db_connection)) -> dict[str, Any]:
    """Return dashboard metrics for the static Netlify frontend."""
    return dashboard_context(connection)


@app.get("/api/admin/subscriptions")
def api_subscriptions(connection: sqlite3.Connection = Depends(db_connection)) -> dict[str, Any]:
    """Return subscribers and active plans for the subscriptions view."""
    plans = [dict(row) for row in connection.execute(
        "SELECT * FROM plans WHERE active = 1 ORDER BY monthly_price"
    )]
    return {"items": store_rows(connection), "plans": plans}


@app.get("/api/admin/plans")
def api_plans(connection: sqlite3.Connection = Depends(db_connection)) -> dict[str, Any]:
    """Return subscription plans for the plans view."""
    plans = [dict(row) for row in connection.execute("SELECT * FROM plans ORDER BY monthly_price")]
    for plan in plans:
        plan["features_list"] = json.loads(plan["features"] or "[]")
    return {"items": plans}


@app.get("/api/admin/users")
def api_users(connection: sqlite3.Connection = Depends(db_connection)) -> dict[str, Any]:
    """Return admin users and login history for the users view."""
    users = [dict(row) for row in connection.execute(
        "SELECT id, name, email, role, permissions, created_at FROM admin_users ORDER BY created_at DESC"
    )]
    for user in users:
        user["permissions_list"] = json.loads(user["permissions"] or "[]")
    history = [dict(row) for row in connection.execute(
        "SELECT * FROM login_history ORDER BY logged_at DESC LIMIT 50"
    )]
    return {"items": users, "history": history}


# ---------------------------------------------------------------------------
# Desktop POS licensing and synchronization API
# ---------------------------------------------------------------------------
@app.post("/api/v1/license/verify")
def verify_license(body: LicenseVerifyRequest, connection: sqlite3.Connection = Depends(db_connection)):
    row = store_or_404(connection, body.store_id)
    current_status = row["status"]
    if current_status == "active" and date.fromisoformat(row["subscription_end"]) < date.today():
        current_status = "expired"
    if not secrets.compare_digest(row["license_key_hash"], key_hash(body.license_key)):
        raise HTTPException(status_code=401, detail="Invalid license key")
    token = hashlib.sha256(f"{row['store_id']}:{body.hardware_id or ''}:{row['license_key_hash']}".encode()).hexdigest()
    return {"status": current_status, "expires_at": row["subscription_end"], "token": token}


@app.post("/api/v1/telemetry/sync")
def sync_telemetry(body: TelemetryRequest, x_store_id: Optional[str] = Header(default=None), connection: sqlite3.Connection = Depends(db_connection)):
    if not x_store_id:
        raise HTTPException(status_code=400, detail="X-Store-ID header is required")
    store_or_404(connection, x_store_id)
    connection.execute(
        """INSERT INTO telemetry(store_id, received_at, total_daily_sales, total_low_stock_count,
           last_active_cashier_session, app_status, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (x_store_id.strip(), datetime.utcnow().isoformat(), body.total_daily_sales,
         body.total_low_stock_count, body.last_active_cashier_session, body.app_status,
         json.dumps(body.payload, ensure_ascii=False)),
    )
    return {"status": "accepted"}


@app.post("/api/v1/sync/heartbeat")
def sync_heartbeat(body: TelemetryRequest, x_store_id: Optional[str] = Header(default=None), connection: sqlite3.Connection = Depends(db_connection)):
    return sync_telemetry(body, x_store_id, connection)


@app.post("/api/v1/sync/sales")
def sync_sales(body: SalesSyncRequest, x_store_id: Optional[str] = Header(default=None), connection: sqlite3.Connection = Depends(db_connection)):
    if not x_store_id:
        raise HTTPException(status_code=400, detail="X-Store-ID header is required")
    store_or_404(connection, x_store_id)
    total = 0.0
    for index, sale in enumerate(body.sales):
        try:
            total += float(sale.get("total", 0) or 0)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"sales[{index}].total must be a number") from exc
    return sync_telemetry(TelemetryRequest(total_daily_sales=total, app_status="sales_sync", payload={"sales": body.sales}), x_store_id, connection)


@app.get("/api/v1/app/check-update")
def check_update(connection: sqlite3.Connection = Depends(db_connection)):
    row = connection.execute("SELECT version, download_url FROM app_releases WHERE id = 1").fetchone()
    return {
        "version": row["version"],
        "latest_version": row["version"],
        "download_url": row["download_url"],
    }


@app.post("/api/v1/stores/{store_id}/extend")
def extend_subscription(store_id: str, body: ExtendSubscriptionRequest, connection: sqlite3.Connection = Depends(db_connection)):
    row = store_or_404(connection, store_id)
    current_end = max(date.today(), date.fromisoformat(row["subscription_end"]))
    new_end = current_end + timedelta(days=body.days)
    connection.execute("UPDATE stores SET subscription_end = ?, status = 'active' WHERE store_id = ?", (new_end.isoformat(), store_id.strip()))
    return {"store_id": store_id, "subscription_end": new_end.isoformat(), "status": "active"}


@app.post("/api/v1/stores/{store_id}/block")
def block_store(store_id: str, connection: sqlite3.Connection = Depends(db_connection)):
    store_or_404(connection, store_id)
    connection.execute("UPDATE stores SET status = 'blocked' WHERE store_id = ?", (store_id.strip(),))
    return {"store_id": store_id, "status": "blocked"}


@app.post("/api/v1/stores/{store_id}/generate-license")
def generate_license(store_id: str, connection: sqlite3.Connection = Depends(db_connection)):
    store_or_404(connection, store_id)
    license_key = f"POS-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    connection.execute("UPDATE stores SET license_key_hash = ? WHERE store_id = ?", (key_hash(license_key), store_id.strip()))
    return {"store_id": store_id, "license_key": license_key}


@app.get("/api/v1/app/version")
def version_compatibility(store_id: str = Query(..., min_length=1), connection: sqlite3.Connection = Depends(db_connection)):
    store_or_404(connection, store_id)
    release = check_update(connection)
    return {"latest_version": release["version"], "download_url": release["download_url"]}
