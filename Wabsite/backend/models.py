"""Validated API models used by the admin portal and desktop POS client."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
    sales: List[Dict[str, Any]] = Field(default_factory=list)


class SubscriberCreateRequest(BaseModel):
    store_name: str = Field(min_length=1, max_length=120)
    owner_name: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=40)
    plan_id: int
    days: int = Field(default=30, ge=1, le=3650)


class PlanCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    monthly_price: float = Field(ge=0)
    annual_price: float = Field(ge=0)
    features: List[str] = Field(default_factory=list)


class AdminUserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=160)
    role: str = Field(default="مشرف", max_length=60)
    permissions: List[str] = Field(default_factory=list)
