from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.data_store import (
    ADDRESSES,
    CATEGORIES,
    MESSAGES,
    PRODUCTS,
    STORES,
    USERS,
)
from backend.models import (
    AddressModel,
    CategoryModel,
    MessageModel,
    ProductModel,
    StoreModel,
    UserModel,
)


def seed_initial_data(db: Session) -> None:
    has_users = db.execute(select(UserModel.id).limit(1)).first() is not None
    if has_users:
        return

    db.add_all(
        [
            UserModel(id=u["id"], name=u["name"], email=u["email"], password=u["password"])
            for u in USERS
        ]
    )
    db.add_all([CategoryModel(id=c.id, name=c.name) for c in CATEGORIES])
    db.add_all(
        [
            StoreModel(
                id=s.id,
                name=s.name,
                rating=s.rating,
                distance=s.distance,
                delivery_time=s.delivery_time,
                is_favorite=s.is_favorite,
            )
            for s in STORES
        ]
    )
    db.commit() # Commit stores first to avoid ForeignKey constraints when adding products

    db.add_all(
        [
            ProductModel(
                id=p.id,
                name=p.name,
                price=p.price,
                unit=p.unit,
                description=p.description,
                store_id=p.store_id,
                store_name=p.store_name,
                category_id=p.category_id,
                is_favorite=p.is_favorite,
            )
            for p in PRODUCTS
        ]
    )
    db.add_all(
        [
            AddressModel(
                id=a.id,
                title=a.title,
                full_address=a.full_address,
                is_default=a.is_default,
            )
            for a in ADDRESSES
        ]
    )
    db.add_all(
        [
            MessageModel(
                id=m.id,
                sender_name=m.sender_name,
                last_message=m.last_message,
                time=m.time,
                is_me=m.is_me,
            )
            for m in MESSAGES
        ]
    )
    db.commit()
