from datetime import date
from uuid import uuid4

from passlib.context import CryptContext

from schemas import (
    Address,
    CartItemResponse,
    Category,
    Message,
    Order,
    Product,
    Store,
    User,
)

# Use pbkdf2_sha256 instead of bcrypt to avoid the 72-byte limit and local issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception:
        # Fallback keeps auth usable if bcrypt backend is unavailable in runtime.
        return f"plain${password}"


def verify_password(plain_password: str, stored_password: str) -> bool:
    # Backward compatibility for existing plain-text seed values.
    if stored_password.startswith("plain$"):
        return plain_password == stored_password.removeprefix("plain$")
    if stored_password.startswith("$pbkdf2"):
        try:
            return pwd_context.verify(plain_password, stored_password)
        except Exception:
            return False
    if stored_password.startswith("$2"):
        try:
            return pwd_context.verify(plain_password, stored_password)
        except Exception:
            return False
    return plain_password == stored_password


USERS: list[dict] = [
    {
        "id": "u1",
        "name": "Demo User",
        "email": "demo@cartify.com",
        "password": hash_password("123456"),
    }
]


CATEGORIES: list[Category] = [
    Category(id="c1", name="Fruits"),
    Category(id="c2", name="Vegetables"),
    Category(id="c3", name="Dairy"),
]


STORES: list[Store] = [
    Store(id="s1", name="Fresh Mart", rating=4.5, distance="1.2 km", delivery_time="20-30 min"),
    Store(id="s2", name="Daily Basket", rating=4.2, distance="2.8 km", delivery_time="25-35 min"),
]


PRODUCTS: list[Product] = [
    Product(
        id="p1",
        name="Apple",
        price=220.0,
        unit="1 kg",
        description="Fresh red apples",
        store_id="s1",
        store_name="Fresh Mart",
        category_id="c1",
    ),
    Product(
        id="p2",
        name="Banana",
        price=160.0,
        unit="1 dozen",
        description="Naturally sweet bananas",
        store_id="s1",
        store_name="Fresh Mart",
        category_id="c1",
    ),
    Product(
        id="p3",
        name="Milk",
        price=210.0,
        unit="1 liter",
        description="Pasteurized milk",
        store_id="s2",
        store_name="Daily Basket",
        category_id="c3",
    ),
]


CART: dict[str, int] = {}


ADDRESSES: list[Address] = [
    Address(id="a1", title="Home", full_address="Street 1, Lahore", is_default=True)
]


ORDERS: list[Order] = []


MESSAGES: list[Message] = [
    Message(id="m1", sender_name="Fresh Mart", last_message="Order ready for dispatch", time="10:30 AM")
]


def get_user_by_email(email: str) -> dict | None:
    return next((u for u in USERS if u["email"].lower() == email.lower()), None)


def add_user(name: str, email: str, password: str) -> User:
    user = {
        "id": f"u{len(USERS) + 1}",
        "name": name,
        "email": email,
        "password": hash_password(password),
    }
    USERS.append(user)
    return User(id=user["id"], name=user["name"], email=user["email"])


def to_user(user: dict) -> User:
    return User(id=user["id"], name=user["name"], email=user["email"])


def get_product(product_id: str) -> Product | None:
    return next((p for p in PRODUCTS if p.id == product_id), None)


def build_cart_response():
    items: list[CartItemResponse] = []
    subtotal = 0.0
    for pid, qty in CART.items():
        product = get_product(pid)
        if product is None:
            continue
        subtotal += product.price * qty
        items.append(CartItemResponse(product=product, quantity=qty))
    delivery_fee = 50.0 if items else 0.0
    return {"items": items, "subtotal": subtotal, "delivery_fee": delivery_fee, "total": subtotal + delivery_fee}


def place_order(address_id: str) -> Order:
    cart = build_cart_response()
    if not cart["items"]:
        raise ValueError("Cart is empty")
    order = Order(
        id=f"ord_{uuid4().hex[:8]}",
        store_name=cart["items"][0].product.store_name,
        status="Processing",
        date=str(date.today()),
        total_amount=cart["total"],
        items=cart["items"],
    )
    address_exists = any(a.id == address_id for a in ADDRESSES)
    if not address_exists:
        raise ValueError("Address not found")
    ORDERS.insert(0, order)
    CART.clear()
    return order
