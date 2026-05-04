import os
from datetime import date
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select, text

from backend.data_store import hash_password, verify_password
from backend.db import DEV_SQLITE_MODE, SessionLocal, engine
from backend.models import (
    AddressModel,
    Base,
    CartItemModel,
    CategoryModel,
    MessageModel,
    OrderModel,
    OrderItemModel,
    ProductModel,
    StoreModel,
    UserModel,
)
from backend.seed import seed_initial_data
from backend.schemas import (
    Address,
    AuthResponse,
    CartItem,
    CartResponse,
    CreateAddressRequest,
    LoginRequest,
    Message,
    Order,
    Product,
    SignupRequest,
    Store,
)

app = FastAPI(title="Cartify Backend", version="1.0.0")

# -------------------- CORS --------------------
allowed_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- STARTUP --------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_initial_data(db)

# -------------------- SIMPLE AUTH PLACEHOLDER --------------------
# NOTE: Replace with JWT auth in production
def get_current_user_id():
    return "u1"  # demo user from seed; TODO: replace with real auth


# -------------------- HEALTH --------------------
def _admin_health_block() -> dict:
    """Dev SQLite par admin mount nahi (Postgres + asyncpg); warna Amis admin `ADMIN_SITE_PATH` par."""
    if DEV_SQLITE_MODE:
        return {
            "mounted": False,
            "reason": "CARTIFY_DEV_SQLITE=1: admin tabhi jab real Postgres/Supabase (dev SQLite par admin mount nahi).",
        }
    path = (os.getenv("ADMIN_SITE_PATH", "/admin") or "/admin").strip()
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")
    return {"mounted": True, "path": path, "title": os.getenv("ADMIN_SITE_TITLE", "Cartify Admin")}


@app.get("/health")
def health_check():
    admin_info = _admin_health_block()
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "admin": admin_info}
    except Exception:
        return {"status": "error", "database": "disconnected", "admin": admin_info}


# -------------------- AUTH --------------------
@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    with SessionLocal() as db:
        user = db.execute(
            select(UserModel).where(UserModel.email == payload.email.lower().strip())
        ).scalar_one_or_none()

        if not user or not verify_password(payload.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {
            "token": f"token-{user.id}",
            "user": {"id": user.id, "name": user.name, "email": user.email},
        }


@app.post("/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    with SessionLocal() as db:
        existing = db.execute(
            select(UserModel).where(UserModel.email == payload.email.lower().strip())
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(status_code=409, detail="Email already exists")

        user = UserModel(
            id=f"u{uuid4().hex[:10]}",
            name=payload.name.strip(),
            email=payload.email.lower().strip(),
            password=hash_password(payload.password),
        )
        db.add(user)
        db.commit()

        return {
            "token": f"token-{user.id}",
            "user": {"id": user.id, "name": user.name, "email": user.email},
        }


# -------------------- CATEGORIES --------------------
@app.get("/categories")
def get_categories():
    with SessionLocal() as db:
        rows = db.execute(select(CategoryModel)).scalars().all()
        return [{"id": c.id, "name": c.name} for c in rows]


# -------------------- STORES --------------------
@app.get("/stores", response_model=list[Store])
def get_stores(search: str | None = None):
    with SessionLocal() as db:
        rows = db.execute(select(StoreModel)).scalars().all()

        data = [
            {
                "id": s.id,
                "name": s.name,
                "rating": s.rating,
                "distance": s.distance,
                "delivery_time": s.delivery_time,
                "is_favorite": s.is_favorite,
            }
            for s in rows
        ]

        if search:
            q = search.lower().strip()
            data = [s for s in data if q in s["name"].lower()]

        return data


@app.get("/stores/{store_id}", response_model=Store)
def get_store_detail(store_id: str):
    with SessionLocal() as db:
        store = db.get(StoreModel, store_id)
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

        return {
            "id": store.id,
            "name": store.name,
            "rating": store.rating,
            "distance": store.distance,
            "delivery_time": store.delivery_time,
            "is_favorite": store.is_favorite,
        }


# -------------------- PRODUCTS --------------------
@app.get("/products", response_model=list[Product])
def get_products(category_id: str | None = None, q: str | None = Query(default=None)):
    with SessionLocal() as db:
        rows = db.execute(select(ProductModel)).scalars().all()

        data = [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "unit": p.unit,
                "description": p.description,
                "store_id": p.store_id,
                "store_name": p.store_name,
                "category_id": p.category_id,
                "is_favorite": p.is_favorite,
            }
            for p in rows
        ]

        if category_id:
            data = [p for p in data if p["category_id"] == category_id]

        if q:
            ql = q.lower()
            data = [p for p in data if ql in p["name"].lower() or ql in p["store_name"].lower()]

        return data


@app.get("/products/{product_id}", response_model=Product)
def get_product_detail(product_id: str):
    with SessionLocal() as db:
        product = db.get(ProductModel, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return product


# -------------------- CART (USER BASED FIXED) --------------------
@app.get("/cart", response_model=CartResponse)
def get_cart():
    user_id = get_current_user_id()

    with SessionLocal() as db:
        rows = db.execute(
            select(CartItemModel).where(CartItemModel.user_id == user_id)
        ).scalars().all()

        items = []
        subtotal = 0.0

        for row in rows:
            product = db.get(ProductModel, row.product_id)
            if not product:
                continue

            items.append(
                {
                    "product": product,
                    "quantity": row.quantity,
                }
            )
            subtotal += product.price * row.quantity

        delivery_fee = 50.0 if items else 0.0

        return {
            "items": items,
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "total": subtotal + delivery_fee,
        }


@app.post("/cart/items", response_model=CartResponse)
def add_cart_item(payload: CartItem):
    user_id = get_current_user_id()

    with SessionLocal() as db:
        product = db.get(ProductModel, payload.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        existing = db.execute(
            select(CartItemModel).where(
                CartItemModel.product_id == payload.product_id,
                CartItemModel.user_id == user_id,
            )
        ).scalar_one_or_none()

        if existing:
            existing.quantity += payload.quantity
        else:
            db.add(
                CartItemModel(
                    product_id=payload.product_id,
                    quantity=payload.quantity,
                    user_id=user_id,
                )
            )

        db.commit()

    return get_cart()


@app.patch("/cart/items/{product_id}", response_model=CartResponse)
def update_cart_item(product_id: str, payload: CartItem):
    user_id = get_current_user_id()

    with SessionLocal() as db:
        item = db.execute(
            select(CartItemModel).where(
                CartItemModel.product_id == product_id,
                CartItemModel.user_id == user_id,
            )
        ).scalar_one_or_none()

        if not item:
            db.add(
                CartItemModel(
                    product_id=product_id,
                    quantity=payload.quantity,
                    user_id=user_id,
                )
            )
        else:
            item.quantity = payload.quantity

        db.commit()

    return get_cart()


@app.delete("/cart/items/{product_id}", response_model=CartResponse)
def delete_cart_item(product_id: str):
    user_id = get_current_user_id()

    with SessionLocal() as db:
        item = db.execute(
            select(CartItemModel).where(
                CartItemModel.product_id == product_id,
                CartItemModel.user_id == user_id,
            )
        ).scalar_one_or_none()

        if item:
            db.delete(item)
            db.commit()

    return get_cart()


# -------------------- ORDERS (FIXED RETURN) --------------------
@app.post("/orders", response_model=Order)
def create_order(payload: Order):
    user_id = get_current_user_id()

    with SessionLocal() as db:
        order_id = f"ord_{uuid4().hex[:8]}"
        order_date = str(date.today())

        if not payload.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        order = OrderModel(
            id=order_id,
            store_name=payload.store_name,
            status="Processing",
            date=order_date,
            total_amount=payload.total_amount,
            user_id=user_id,
        )
        db.add(order)

        for item in payload.items:
            db.add(
                OrderItemModel(
                    order_id=order_id,
                    product_id=item.product.id,
                    quantity=item.quantity,
                )
            )

        # clear only this user's cart
        db.execute(
            delete(CartItemModel).where(CartItemModel.user_id == user_id)
        )

        db.commit()

    return get_order_detail(order_id)


@app.get("/orders", response_model=list[Order])
def get_orders():
    user_id = get_current_user_id()
    with SessionLocal() as db:
        rows = db.execute(
            select(OrderModel).where(OrderModel.user_id == user_id)
        ).scalars().all()
        # Order schema ko items chahiye; list view par khali items (detail /orders/{id} par poori list)
        return [
            {
                "id": o.id,
                "store_name": o.store_name,
                "status": o.status,
                "date": o.date,
                "total_amount": o.total_amount,
                "items": [],
            }
            for o in rows
        ]


@app.get("/orders/{order_id}", response_model=Order)
def get_order_detail(order_id: str):
    user_id = get_current_user_id()
    with SessionLocal() as db:
        order = db.get(OrderModel, order_id)
        if not order or order.user_id != user_id:
            raise HTTPException(status_code=404, detail="Order not found")

        rows = db.execute(
            select(OrderItemModel).where(OrderItemModel.order_id == order_id)
        ).scalars().all()

        items_payload = []
        for it in rows:
            product = db.get(ProductModel, it.product_id)
            if not product:
                continue
            items_payload.append({"product": product, "quantity": it.quantity})

        return {
            "id": order.id,
            "store_name": order.store_name,
            "status": order.status,
            "date": order.date,
            "total_amount": order.total_amount,
            "items": items_payload,
        }


# -------------------- MESSAGES --------------------
@app.get("/messages", response_model=list[Message])
def get_messages():
    with SessionLocal() as db:
        rows = db.execute(select(MessageModel)).scalars().all()
        return rows


# -------------------- ADDRESSES --------------------
@app.get("/addresses", response_model=list[Address])
def get_addresses():
    with SessionLocal() as db:
        rows = db.execute(select(AddressModel)).scalars().all()
        return rows


@app.post("/addresses", response_model=list[Address])
def create_address(payload: CreateAddressRequest):
    with SessionLocal() as db:
        if payload.is_default:
            for a in db.execute(select(AddressModel)).scalars().all():
                a.is_default = False

        addr = AddressModel(
            id=f"a{uuid4().hex[:10]}",
            title=payload.title,
            full_address=payload.full_address,
            is_default=payload.is_default,
        )
        db.add(addr)
        db.commit()

    return get_addresses()


@app.delete("/addresses/{address_id}", response_model=list[Address])
def delete_address(address_id: str):
    with SessionLocal() as db:
        addr = db.get(AddressModel, address_id)
        if not addr:
            raise HTTPException(status_code=404, detail="Not found")

        db.delete(addr)
        db.commit()

    return get_addresses()


# -------------------- ADMIN (Amis; Postgres only — dev SQLite par skip) --------------------
if not DEV_SQLITE_MODE:
    from backend.admin_site import mount_cartify_admin

    mount_cartify_admin(app)


# -------------------- VERCEL HANDLER --------------------
from mangum import Mangum

handler = Mangum(app)