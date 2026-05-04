from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    id: str
    name: str
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=3)


class SignupRequest(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)


class AuthResponse(BaseModel):
    token: str
    user: User


class Category(BaseModel):
    id: str
    name: str


class Store(BaseModel):
    id: str
    name: str
    rating: float
    distance: str
    delivery_time: str
    is_favorite: bool = False


class Product(BaseModel):
    id: str
    name: str
    price: float
    unit: str
    description: str
    store_id: str
    store_name: str
    category_id: str
    is_favorite: bool = False


class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


class CartItemResponse(BaseModel):
    product: Product
    quantity: int


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    subtotal: float
    delivery_fee: float
    total: float


class Address(BaseModel):
    id: str
    title: str
    full_address: str
    is_default: bool = False


class CreateAddressRequest(BaseModel):
    title: str
    full_address: str
    is_default: bool = False


class Order(BaseModel):
    id: str
    store_name: str
    status: str
    date: str
    total_amount: float
    items: list[CartItemResponse]


class CheckoutRequest(BaseModel):
    address_id: str
    payment_method: str


class Message(BaseModel):
    id: str
    sender_name: str
    last_message: str
    time: str
    is_me: bool = False
