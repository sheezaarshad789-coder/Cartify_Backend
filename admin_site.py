"""
Cartify Admin UI Configuration (FastAPI-Amis-Admin)
Project: Cartify - Final Year Project
Organization: DevSquad
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi_amis_admin.admin import admin
from fastapi_amis_admin.admin.settings import Settings
from fastapi_amis_admin.admin.site import AdminSite
from sqlalchemy_database import AsyncDatabase

# Local imports
try:
    from data_store import hash_password
    from models import (
        AddressModel,
        CartItemModel,
        CategoryModel,
        MessageModel,
        OrderItemModel,
        OrderModel,
        ProductModel,
        StoreModel,
        UserModel,
    )
except ImportError as e:
    print(f"⚠️ Model Import Warning: {e}")

# Logger setup
logger = logging.getLogger("cartify_admin")


def _ensure_entity_id(data: dict, prefix: str) -> dict:
    """
    AMIS create form mein agar id empty ho to safe unique id generate karo.
    """
    if not data.get("id"):
        data["id"] = f"{prefix}{uuid4().hex[:10]}"
    return data

def _prepare_db_url() -> str:
    """
    Same logical DB as `db.py` (sync API): Postgres async URL for admin, or SQLite+aiosqlite when dev / auto-fallback.
    """
    from db import DATABASE_URL as sync_database_url
    from db import DEV_SQLITE_MODE

    if DEV_SQLITE_MODE or str(sync_database_url).startswith("sqlite"):
        sqlite_file = Path(__file__).resolve().parent / "cartify_dev.db"
        return f"sqlite+aiosqlite:///{sqlite_file.as_posix()}"

    raw = os.getenv("DATABASE_URL", "").strip()
    
    if not raw:
        # Fallback for local development
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    
    # Remove quotes if present in .env
    raw = raw.replace('"', '').replace("'", "")

    # Fix the driver prefix for Async support
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif raw.startswith("postgresql+psycopg2://"):
        raw = raw.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        
    return raw

def _admin_async_engine() -> AsyncDatabase:
    """
    Async engine configuration with SSL support and error handling.
    """
    url = _prepare_db_url()
    
    connect_args = {}
    if url.startswith("postgresql+"):
        # Supabase usually requires SSL.
        connect_args = {"ssl": "require"}
    
    try:
        return AsyncDatabase.create(
            url,
            echo=os.getenv("ADMIN_DEBUG", "false").lower() == "true",
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args,
        )
    except Exception as e:
        logger.error(f"❌ Failed to create database engine: {e}")
        raise e

def build_admin_site() -> AdminSite:
    """
    Main Factory to build the Admin UI.
    """
    db_url = _prepare_db_url()
    
    # Vercel/Render/Local Read-only fix for uploads
    temp_upload_dir = os.path.join(tempfile.gettempdir(), "amis_uploads")
    if not os.path.exists(temp_upload_dir):
        try:
            os.makedirs(temp_upload_dir, exist_ok=True)
        except Exception:
            temp_upload_dir = "." # Fallback to current dir if /tmp fails

    settings = Settings(
        site_title=os.getenv("ADMIN_SITE_TITLE", "Cartify Admin"),
        site_path=os.getenv("ADMIN_SITE_PATH", "/admin"),
        language=os.getenv("ADMIN_LANGUAGE", "en_US"),
        database_url_async=db_url,
        file_directory=temp_upload_dir,
    )
    
    site = AdminSite(settings=settings, engine=_admin_async_engine())

    # --- Model Registrations ---

    @site.register_admin
    class CategoryAdmin(admin.ModelAdmin):
        page_schema = "Categories"
        model = CategoryModel
        icon = "fa fa-list"
        list_display = [CategoryModel.id, CategoryModel.name]
        search_fields = [CategoryModel.name]

        async def on_create_pre(self, request, obj, **kwargs):
            data = await super().on_create_pre(request, obj, **kwargs)
            return _ensure_entity_id(data, "c")

    @site.register_admin
    class StoreAdmin(admin.ModelAdmin):
        page_schema = "Stores"
        model = StoreModel
        icon = "fa fa-store"
        list_display = [StoreModel.id, StoreModel.name]

        async def on_create_pre(self, request, obj, **kwargs):
            data = await super().on_create_pre(request, obj, **kwargs)
            return _ensure_entity_id(data, "s")

    @site.register_admin
    class ProductAdmin(admin.ModelAdmin):
        page_schema = "Products"
        model = ProductModel
        icon = "fa fa-shopping-bag"
        search_fields = [ProductModel.name]
        list_display = [ProductModel.id, ProductModel.name, ProductModel.price]

        async def on_create_pre(self, request, obj, **kwargs):
            data = await super().on_create_pre(request, obj, **kwargs)
            return _ensure_entity_id(data, "p")

    @site.register_admin
    class UserAdmin(admin.ModelAdmin):
        page_schema = "Users"
        model = UserModel
        icon = "fa fa-users"
        list_display = [UserModel.id, UserModel.name, UserModel.email]
        search_fields = [UserModel.email, UserModel.name]

        async def on_create_pre(self, request, obj, **kwargs):
            data = await super().on_create_pre(request, obj, **kwargs)
            data = _ensure_entity_id(data, "u")
            pw = data.get("password")
            if pw:
                data["password"] = hash_password(str(pw))
            return data

        async def on_update_pre(self, request, obj, item_id, **kwargs):
            data = await super().on_update_pre(request, obj, item_id, **kwargs)
            pw = data.get("password")
            if pw:
                data["password"] = hash_password(str(pw))
            return data

    @site.register_admin
    class OrderAdmin(admin.ModelAdmin):
        page_schema = "Orders"
        model = OrderModel
        icon = "fa fa-truck"
        list_filter = [OrderModel.status]

        async def on_create_pre(self, request, obj, **kwargs):
            data = await super().on_create_pre(request, obj, **kwargs)
            return _ensure_entity_id(data, "ord_")

    @site.register_admin
    class OrderItemAdmin(admin.ModelAdmin):
        page_schema = "Order Items"
        model = OrderItemModel

    @site.register_admin
    class AddressAdmin(admin.ModelAdmin):
        page_schema = "Addresses"
        model = AddressModel
        icon = "fa fa-map-marker"

        async def on_create_pre(self, request, obj, **kwargs):
            data = await super().on_create_pre(request, obj, **kwargs)
            return _ensure_entity_id(data, "a")

    @site.register_admin
    class MessageAdmin(admin.ModelAdmin):
        page_schema = "Messages"
        model = MessageModel
        icon = "fa fa-envelope"

        async def on_create_pre(self, request, obj, **kwargs):
            data = await super().on_create_pre(request, obj, **kwargs)
            return _ensure_entity_id(data, "m")

    @site.register_admin
    class CartItemAdmin(admin.ModelAdmin):
        page_schema = "Cart Analytics"
        model = CartItemModel

    return site

# Singleton instance
_admin_site: Optional[AdminSite] = None

def get_admin_site() -> AdminSite:
    global _admin_site
    if _admin_site is None:
        _admin_site = build_admin_site()
    return _admin_site

def mount_cartify_admin(app: FastAPI) -> None:
    """
    Call this in main.py: mount_cartify_admin(app)
    """
    try:
        admin_instance = get_admin_site()
        admin_instance.mount_app(app)
    except Exception as e:
        logger.error(f"❌ Critical Error mounting Admin: {e}")

if __name__ == "__main__":
    print("Cartify Admin Module Loaded Successfully.")