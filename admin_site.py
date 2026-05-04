"""Cartify admin UI (FastAPI-Amis-Admin) — wohi Supabase/Postgres connection jo `db.py` use karti hai."""

import os

from fastapi import FastAPI
from fastapi_amis_admin.admin import admin
from fastapi_amis_admin.admin.settings import Settings
from fastapi_amis_admin.admin.site import AdminSite
from sqlalchemy_database import AsyncDatabase

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


def _async_supabase_url() -> str:
    """Sync `DATABASE_URL` (psycopg2) ko asyncpg admin engine ke liye map karta hai."""
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        raise RuntimeError("DATABASE_URL required (same as backend/db.py / Supabase).")
    if raw.startswith("postgresql+psycopg2://"):
        return raw.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "postgresql+asyncpg://" in raw:
        return raw
    raise RuntimeError("DATABASE_URL must be a PostgreSQL URL for the admin engine.")


def _admin_async_engine() -> AsyncDatabase:
    url = _async_supabase_url()
    return AsyncDatabase.create(
        url,
        echo=os.getenv("ADMIN_DEBUG", "false").lower() == "true",
        pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "300")),
        connect_args={"ssl": True},
    )


def build_admin_site() -> AdminSite:
    db_url = _async_supabase_url()
    settings = Settings(
        site_title=os.getenv("ADMIN_SITE_TITLE", "Cartify Admin"),
        site_path=os.getenv("ADMIN_SITE_PATH", "/admin"),
        language=os.getenv("ADMIN_LANGUAGE", "en_US"),
        database_url_async=db_url,
    )
    site = AdminSite(settings=settings, engine=_admin_async_engine())

    @site.register_admin
    class CategoryAdmin(admin.ModelAdmin):
        page_schema = "Categories"
        model = CategoryModel

    @site.register_admin
    class StoreAdmin(admin.ModelAdmin):
        page_schema = "Stores"
        model = StoreModel

    @site.register_admin
    class ProductAdmin(admin.ModelAdmin):
        page_schema = "Products"
        model = ProductModel
        search_fields = [ProductModel.name, ProductModel.store_name]

    @site.register_admin
    class UserAdmin(admin.ModelAdmin):
        page_schema = "Users"
        model = UserModel
        list_display = [UserModel.id, UserModel.name, UserModel.email]
        search_fields = [UserModel.email, UserModel.name]

        async def on_create_pre(self, request, obj, **kwargs):
            data = await super().on_create_pre(request, obj, **kwargs)
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

    @site.register_admin
    class OrderItemAdmin(admin.ModelAdmin):
        page_schema = "Order items"
        model = OrderItemModel

    @site.register_admin
    class AddressAdmin(admin.ModelAdmin):
        page_schema = "Addresses"
        model = AddressModel

    @site.register_admin
    class MessageAdmin(admin.ModelAdmin):
        page_schema = "Messages"
        model = MessageModel

    @site.register_admin
    class CartItemAdmin(admin.ModelAdmin):
        page_schema = "Cart items"
        model = CartItemModel

    return site


_admin_site: AdminSite | None = None


def get_admin_site() -> AdminSite:
    global _admin_site
    if _admin_site is None:
        _admin_site = build_admin_site()
    return _admin_site


def mount_cartify_admin(app: FastAPI) -> None:
    get_admin_site().mount_app(app)
