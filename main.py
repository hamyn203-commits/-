"""
Pharmacy Management System - Backend API
FastAPI + SQLAlchemy + SQLite
Integrated with Payments System
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum
import uvicorn
import logging
import json
import os
import hashlib
import urllib.parse
import webbrowser

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== DATABASE SETUP ==========
DATABASE_URL = "sqlite:///./pharmacy.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========== MODELS ==========
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    products = relationship("Product", back_populates="category_obj")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, default="")
    address = Column(String, default="")
    company = Column(String, default="")
    balance = Column(Float, default=0.0)
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)

    purchases = relationship("Purchase", back_populates="supplier")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    barcode = Column(String, unique=True, index=True)
    category = Column(String, default="عام")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    company = Column(String, default="غير محدد")
    quantity = Column(Integer, default=0)
    unit_price = Column(Float, default=0.0)
    expiry_date = Column(String, nullable=True)
    image_path = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    product_images_json = Column(String, default="")
    description = Column(String, default="")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    category_obj = relationship("Category", back_populates="products")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    total_amount = Column(Float, default=0.0)
    amount_paid = Column(Float, default=0.0)
    remaining_amount = Column(Float, default=0.0)
    status = Column(String, default="unpaid")
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)

    supplier = relationship("Supplier", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product")

class Pharmacy(Base):
    __tablename__ = "pharmacies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    account_status = Column(String, default="active")  # pending | active | blocked | deleted
    approved_at = Column(DateTime, nullable=True)
    blocked_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    device_id = Column(String, nullable=True)
    
    orders = relationship("Order", back_populates="pharmacy")
    payments = relationship("Payment", back_populates="pharmacy")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, nullable=False)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"))
    total_amount = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    discount_type = Column(String, default="value")
    final_total = Column(Float, default=0.0)
    balance_before = Column(Float, default=0.0)
    balance_after = Column(Float, default=0.0)
    status = Column(String, default="pending")
    delivery_person = Column(String, default="")
    notes = Column(String, default="")
    last_status_update = Column(DateTime, nullable=True)
    expected_delivery_note = Column(String, default="")
    payment_status = Column(String, default="unpaid")
    payment_type = Column(String, default="")
    amount_paid = Column(Float, default=0.0)
    remaining_amount = Column(Float, default=0.0)
    payment_notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)
    
    pharmacy = relationship("Pharmacy", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    amount = Column(Float, nullable=False)
    payment_status = Column(String, default="partial")
    payment_type = Column(String, default="cash")
    amount_paid = Column(Float, default=0.0)
    remaining_amount = Column(Float, default=0.0)
    payment_notes = Column(String, default="")
    date = Column(DateTime, default=datetime.now)
    
    pharmacy = relationship("Pharmacy", back_populates="payments")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="admin")
    created_at = Column(DateTime, default=datetime.now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, default="system")
    action = Column(String, nullable=False)
    entity = Column(String, default="")
    entity_id = Column(String, default="")
    details = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    old_status = Column(String, default="")
    new_status = Column(String, nullable=False)
    note = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)


class OrderStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    IN_STORE = "in_store"
    WITH_DRIVER = "with_driver"
    ON_THE_WAY = "on_the_way"
    DELIVERED = "delivered"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


VALID_ORDER_STATUSES = [status.value for status in OrderStatus]
VALID_PAYMENT_TYPES = {"cash", "partial", "full", "deferred", "collect_on_delivery"}
VALID_PAYMENT_STATUSES = {"unpaid", "partial", "full", "deferred", "collect_on_delivery"}
LEGACY_ORDER_STATUS_MAP = {
    "approved": OrderStatus.REVIEWED.value,
    "rejected": OrderStatus.CANCELLED.value,
    "completed": OrderStatus.DELIVERED.value,
}
DEFAULT_ON_THE_WAY_NOTE = "الطلب في الطريق إليك، ومتوقع وصوله خلال 30 إلى 60 دقيقة"


def normalize_order_status(status_value: str) -> str:
    status_value = (status_value or OrderStatus.PENDING.value).lower()
    return LEGACY_ORDER_STATUS_MAP.get(status_value, status_value)


def calculate_payment_status(amount_paid: float, total_due: float, payment_type: str = "cash") -> str:
    amount_paid = float(amount_paid or 0.0)
    total_due = max(float(total_due or 0.0), 0.0)
    payment_type = (payment_type or "cash").lower()
    if payment_type in ("deferred", "collect_on_delivery") and amount_paid <= 0:
        return payment_type
    if amount_paid <= 0:
        return "unpaid"
    if amount_paid + 0.0001 >= total_due:
        return "full"
    return "partial"


def hash_password(password: str) -> str:
    """Hash a password with SHA-256 for local desktop authentication."""
    return hashlib.sha256(str(password or "").encode("utf-8")).hexdigest()


def verify_password(raw_password: str, stored_password: str) -> bool:
    """Accept hashed passwords and legacy plain admin passwords."""
    stored_password = stored_password or ""
    return stored_password == hash_password(raw_password) or stored_password == raw_password

# ========== ENSURE DATABASE SCHEMA ==========
def ensure_database_schema():
    """تأكد من وجود جميع الأعمدة المطلوبة في قاعدة البيانات"""
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS categories ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR UNIQUE NOT NULL, "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            ))
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS suppliers ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR NOT NULL, "
                "phone VARCHAR DEFAULT '', "
                "address VARCHAR DEFAULT '', "
                "company VARCHAR DEFAULT '', "
                "balance FLOAT DEFAULT 0.0, "
                "notes TEXT DEFAULT '', "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            ))
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS purchases ("
                "id INTEGER PRIMARY KEY, "
                "invoice_number VARCHAR UNIQUE NOT NULL, "
                "supplier_id INTEGER NOT NULL, "
                "total_amount FLOAT DEFAULT 0.0, "
                "amount_paid FLOAT DEFAULT 0.0, "
                "remaining_amount FLOAT DEFAULT 0.0, "
                "status VARCHAR DEFAULT 'unpaid', "
                "notes TEXT DEFAULT '', "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            ))
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS purchase_items ("
                "id INTEGER PRIMARY KEY, "
                "purchase_id INTEGER, "
                "product_id INTEGER, "
                "quantity INTEGER DEFAULT 1, "
                "unit_cost FLOAT DEFAULT 0.0, "
                "total_cost FLOAT DEFAULT 0.0)"
            ))

            # التحقق من جدول products
            result = conn.execute(text("PRAGMA table_info(products)")).fetchall()
            existing_columns = [row[1] for row in result]
            
            columns_to_add = {
                "barcode": "ALTER TABLE products ADD COLUMN barcode VARCHAR",
                "category": "ALTER TABLE products ADD COLUMN category VARCHAR DEFAULT 'عام'",
                "category_id": "ALTER TABLE products ADD COLUMN category_id INTEGER",
                "company": "ALTER TABLE products ADD COLUMN company VARCHAR DEFAULT 'غير محدد'",
                "unit_price": "ALTER TABLE products ADD COLUMN unit_price FLOAT DEFAULT 0.0",
                "expiry_date": "ALTER TABLE products ADD COLUMN expiry_date VARCHAR",
                "image_path": "ALTER TABLE products ADD COLUMN image_path VARCHAR",
                "image_url": "ALTER TABLE products ADD COLUMN image_url VARCHAR",
                "product_images_json": "ALTER TABLE products ADD COLUMN product_images_json TEXT DEFAULT ''",
                "description": "ALTER TABLE products ADD COLUMN description TEXT DEFAULT ''",
                "is_active": "ALTER TABLE products ADD COLUMN is_active INTEGER DEFAULT 1",
                "created_at": "ALTER TABLE products ADD COLUMN created_at DATETIME",
                "updated_at": "ALTER TABLE products ADD COLUMN updated_at DATETIME"
            }
            
            for col, sql in columns_to_add.items():
                if col not in existing_columns:
                    try:
                        conn.execute(text(sql))
                        logger.info(f"Added column {col} to products table")
                    except Exception as e:
                        logger.warning(f"Could not add column {col}: {e}")
            
            # تحديث القيم القديمة NULL في products
            try:
                conn.execute(text("UPDATE products SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
                conn.execute(text("UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
                conn.execute(text("UPDATE products SET unit_price = 0.0 WHERE unit_price IS NULL"))
                conn.execute(text("UPDATE products SET quantity = 0 WHERE quantity IS NULL"))
                conn.execute(text("UPDATE products SET is_active = 1 WHERE is_active IS NULL"))
                conn.execute(text("UPDATE products SET product_images_json = '' WHERE product_images_json IS NULL"))
                conn.execute(text("UPDATE products SET description = '' WHERE description IS NULL"))
                conn.execute(text(
                    "INSERT OR IGNORE INTO categories (name, created_at) "
                    "SELECT DISTINCT COALESCE(NULLIF(category, ''), 'عام'), CURRENT_TIMESTAMP FROM products"
                ))
                conn.execute(text(
                    "UPDATE products SET category_id = ("
                    "SELECT categories.id FROM categories WHERE categories.name = products.category"
                    ") WHERE category_id IS NULL AND category IS NOT NULL AND category != ''"
                ))
                logger.info("Updated NULL values in products table")
            except Exception as e:
                logger.warning(f"Could not update NULL values in products: {e}")
            
            # التحقق من جدول pharmacies
            result = conn.execute(text("PRAGMA table_info(pharmacies)")).fetchall()
            existing_columns = [row[1] for row in result]
            
            pharmacies_columns_to_add = {
                "created_at": "ALTER TABLE pharmacies ADD COLUMN created_at DATETIME",
                "account_status": "ALTER TABLE pharmacies ADD COLUMN account_status VARCHAR DEFAULT 'active'",
                "approved_at": "ALTER TABLE pharmacies ADD COLUMN approved_at DATETIME",
                "blocked_at": "ALTER TABLE pharmacies ADD COLUMN blocked_at DATETIME",
                "last_login_at": "ALTER TABLE pharmacies ADD COLUMN last_login_at DATETIME",
                "device_id": "ALTER TABLE pharmacies ADD COLUMN device_id VARCHAR",
            }

            for col, sql in pharmacies_columns_to_add.items():
                if col not in existing_columns:
                    try:
                        conn.execute(text(sql))
                        logger.info(f"Added {col} to pharmacies table")
                    except Exception as e:
                        logger.warning(f"Could not add {col} to pharmacies: {e}")
            
            # تحديث القيم القديمة NULL في pharmacies
            try:
                conn.execute(text("UPDATE pharmacies SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
                conn.execute(text(
                    "UPDATE pharmacies SET account_status = 'active' "
                    "WHERE account_status IS NULL OR account_status = ''"
                ))
                logger.info("Updated NULL values in pharmacies table")
            except Exception as e:
                logger.warning(f"Could not update NULL values in pharmacies: {e}")
            
            # التحقق من جدول orders
            result = conn.execute(text("PRAGMA table_info(orders)")).fetchall()
            existing_columns = [row[1] for row in result]
            
            orders_columns = {
                "order_number": "ALTER TABLE orders ADD COLUMN order_number VARCHAR",
                "total_amount": "ALTER TABLE orders ADD COLUMN total_amount FLOAT DEFAULT 0.0",
                "discount": "ALTER TABLE orders ADD COLUMN discount FLOAT DEFAULT 0.0",
                "discount_type": "ALTER TABLE orders ADD COLUMN discount_type VARCHAR DEFAULT 'value'",
                "final_total": "ALTER TABLE orders ADD COLUMN final_total FLOAT DEFAULT 0.0",
                "balance_before": "ALTER TABLE orders ADD COLUMN balance_before FLOAT DEFAULT 0.0",
                "balance_after": "ALTER TABLE orders ADD COLUMN balance_after FLOAT DEFAULT 0.0",
                "delivery_person": "ALTER TABLE orders ADD COLUMN delivery_person VARCHAR DEFAULT ''",
                "notes": "ALTER TABLE orders ADD COLUMN notes TEXT DEFAULT ''",
                "last_status_update": "ALTER TABLE orders ADD COLUMN last_status_update DATETIME",
                "expected_delivery_note": "ALTER TABLE orders ADD COLUMN expected_delivery_note TEXT DEFAULT ''",
                "payment_status": "ALTER TABLE orders ADD COLUMN payment_status VARCHAR DEFAULT 'unpaid'",
                "payment_type": "ALTER TABLE orders ADD COLUMN payment_type VARCHAR DEFAULT ''",
                "amount_paid": "ALTER TABLE orders ADD COLUMN amount_paid FLOAT DEFAULT 0.0",
                "remaining_amount": "ALTER TABLE orders ADD COLUMN remaining_amount FLOAT DEFAULT 0.0",
                "payment_notes": "ALTER TABLE orders ADD COLUMN payment_notes TEXT DEFAULT ''",
                "created_at": "ALTER TABLE orders ADD COLUMN created_at DATETIME"
            }
            
            for col, sql in orders_columns.items():
                if col not in existing_columns:
                    try:
                        conn.execute(text(sql))
                        logger.info(f"Added column {col} to orders table")
                    except Exception as e:
                        logger.warning(f"Could not add column {col}: {e}")
            
            # تحديث القيم القديمة NULL في orders
            try:
                conn.execute(text("UPDATE orders SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
                conn.execute(text("UPDATE orders SET discount = 0.0 WHERE discount IS NULL"))
                conn.execute(text("UPDATE orders SET discount_type = 'value' WHERE discount_type IS NULL"))
                conn.execute(text("UPDATE orders SET final_total = total_amount WHERE final_total IS NULL OR final_total = 0"))
                conn.execute(text("UPDATE orders SET delivery_person = '' WHERE delivery_person IS NULL"))
                conn.execute(text("UPDATE orders SET notes = '' WHERE notes IS NULL"))
                conn.execute(text("UPDATE orders SET expected_delivery_note = '' WHERE expected_delivery_note IS NULL"))
                conn.execute(text("UPDATE orders SET payment_status = 'unpaid' WHERE payment_status IS NULL OR payment_status = ''"))
                conn.execute(text("UPDATE orders SET payment_type = '' WHERE payment_type IS NULL"))
                conn.execute(text("UPDATE orders SET amount_paid = 0.0 WHERE amount_paid IS NULL"))
                conn.execute(text("UPDATE orders SET remaining_amount = final_total WHERE remaining_amount IS NULL OR remaining_amount = 0"))
                conn.execute(text("UPDATE orders SET payment_notes = '' WHERE payment_notes IS NULL"))
                logger.info("Updated NULL values in orders table")
            except Exception as e:
                logger.warning(f"Could not update NULL values in orders: {e}")
            
            # التحقق من جدول order_items
            result = conn.execute(text("PRAGMA table_info(order_items)")).fetchall()
            existing_columns = [row[1] for row in result]
            
            order_items_columns = {
                "unit_price": "ALTER TABLE order_items ADD COLUMN unit_price FLOAT DEFAULT 0.0",
                "total_price": "ALTER TABLE order_items ADD COLUMN total_price FLOAT DEFAULT 0.0"
            }
            
            for col, sql in order_items_columns.items():
                if col not in existing_columns:
                    try:
                        conn.execute(text(sql))
                        logger.info(f"Added column {col} to order_items table")
                    except Exception as e:
                        logger.warning(f"Could not add column {col}: {e}")

            # التحقق من جدول payments
            result = conn.execute(text("PRAGMA table_info(payments)")).fetchall()
            existing_columns = [row[1] for row in result]
            payment_columns = {
                "order_id": "ALTER TABLE payments ADD COLUMN order_id INTEGER",
                "payment_status": "ALTER TABLE payments ADD COLUMN payment_status VARCHAR DEFAULT 'partial'",
                "payment_type": "ALTER TABLE payments ADD COLUMN payment_type VARCHAR DEFAULT 'cash'",
                "amount_paid": "ALTER TABLE payments ADD COLUMN amount_paid FLOAT DEFAULT 0.0",
                "remaining_amount": "ALTER TABLE payments ADD COLUMN remaining_amount FLOAT DEFAULT 0.0",
                "payment_notes": "ALTER TABLE payments ADD COLUMN payment_notes TEXT DEFAULT ''",
            }
            for col, sql in payment_columns.items():
                if col not in existing_columns:
                    try:
                        conn.execute(text(sql))
                        logger.info(f"Added column {col} to payments table")
                    except Exception as e:
                        logger.warning(f"Could not add column {col} to payments: {e}")
            try:
                conn.execute(text("UPDATE payments SET payment_status = 'partial' WHERE payment_status IS NULL OR payment_status = ''"))
                conn.execute(text("UPDATE payments SET payment_type = 'cash' WHERE payment_type IS NULL OR payment_type = ''"))
                conn.execute(text("UPDATE payments SET amount_paid = amount WHERE amount_paid IS NULL OR amount_paid = 0"))
                conn.execute(text("UPDATE payments SET remaining_amount = 0.0 WHERE remaining_amount IS NULL"))
                conn.execute(text("UPDATE payments SET payment_notes = '' WHERE payment_notes IS NULL"))
            except Exception as e:
                logger.warning(f"Could not update NULL values in payments: {e}")
            
            conn.commit()
            try:
                password_hash = hash_password("admin")
                conn.execute(text(
                    "INSERT OR IGNORE INTO users (username, password, role, created_at) "
                    "VALUES (:username, :password, :role, CURRENT_TIMESTAMP)"
                ), {"username": "admin", "password": password_hash, "role": "admin"})
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not seed admin user: {e}")
            
    except Exception as e:
        logger.error(f"Error ensuring database schema: {e}")
        logger.warning("If schema issues persist, delete pharmacy.db and restart the server")

# إنشاء الجداول
Base.metadata.create_all(bind=engine)
ensure_database_schema()

# ========== PYDANTIC SCHEMAS ==========
class ProductCreate(BaseModel):
    name: str
    quantity: int
    price: Optional[float] = None
    unit_price: Optional[float] = None
    barcode: Optional[str] = None
    category: Optional[str] = "عام"
    category_id: Optional[int] = None
    company: Optional[str] = "غير محدد"
    expiry_date: Optional[str] = None
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    images: Optional[List[str]] = None
    product_images_json: Optional[str] = None
    description: Optional[str] = ""
    is_active: Optional[int] = 1
    
    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True


class SupplierCreate(BaseModel):
    name: str
    phone: Optional[str] = ""
    address: Optional[str] = ""
    company: Optional[str] = ""
    balance: float = 0.0
    notes: Optional[str] = ""


class SupplierResponse(BaseModel):
    id: int
    name: str
    phone: str = ""
    address: str = ""
    company: str = ""
    balance: float = 0.0
    notes: str = ""
    purchases_count: int = 0
    created_at: datetime

    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True


class PurchaseItemCreate(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float


class PurchaseCreate(BaseModel):
    supplier_id: int
    items: List[PurchaseItemCreate]
    invoice_number: Optional[str] = None
    amount_paid: float = 0.0
    notes: Optional[str] = ""


class PurchaseItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_cost: float
    total_cost: float


class PurchaseResponse(BaseModel):
    id: int
    invoice_number: str
    supplier_id: int
    supplier_name: str
    total_amount: float
    amount_paid: float
    remaining_amount: float
    status: str
    notes: str = ""
    created_at: datetime
    items: List[PurchaseItemResponse] = []

class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    unit_price: float
    quantity: int
    expiry_date: Optional[str] = None
    barcode: Optional[str] = None
    category: Optional[str] = "عام"
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    company: Optional[str] = "غير محدد"
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    images: List[str] = []
    product_images_json: Optional[str] = None
    description: Optional[str] = ""
    is_active: int = 1
    created_at: datetime
    updated_at: datetime
    
    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True


class CategoryCreate(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    product_count: int = 0

    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True

class PharmacyCreate(BaseModel):
    name: str
    address: str
    phone: str
    balance: float = 0.0

class PharmacyResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: str
    balance: float
    created_at: datetime
    account_status: str = "active"
    approved_at: Optional[datetime] = None
    blocked_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    device_id: Optional[str] = None
    
    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True


class PharmacyAccountAction(BaseModel):
    note: Optional[str] = ""

class PaymentCreate(BaseModel):
    pharmacy_id: int
    amount: float
    order_id: Optional[int] = None
    payment_status: Optional[str] = None
    payment_type: str = "cash"
    amount_paid: Optional[float] = None
    remaining_amount: Optional[float] = None
    payment_notes: str = ""

class PaymentResponse(BaseModel):
    id: int
    pharmacy_id: int
    order_id: Optional[int] = None
    amount: float
    payment_status: str = "partial"
    payment_type: str = "cash"
    amount_paid: float = 0.0
    remaining_amount: float = 0.0
    payment_notes: str = ""
    new_balance: Optional[float] = None
    date: datetime
    
    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    price: Optional[float] = None
    unit_price: Optional[float] = None

class OrderCreate(BaseModel):
    pharmacy_id: int
    items: List[OrderItemCreate]
    discount: float = 0.0
    discount_type: str = "value"
    delivery_person: Optional[str] = ""
    notes: Optional[str] = ""
    expected_delivery_note: Optional[str] = ""

class OrderStatusUpdate(BaseModel):
    status: str
    delivery_person: Optional[str] = None
    notes: Optional[str] = None
    expected_delivery_note: Optional[str] = None

class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float
    unit_price: float
    total: float
    total_price: float
    
    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True

class OrderResponse(BaseModel):
    id: int
    order_number: str
    pharmacy_id: int
    pharmacy_name: str
    total: float
    total_amount: float
    total_price: float
    discount: float = 0.0
    discount_type: str = "value"
    final_total: float = 0.0
    status: str
    delivery_person: str = ""
    notes: str = ""
    last_status_update: Optional[datetime] = None
    expected_delivery_note: str = ""
    payment_status: str = "unpaid"
    payment_type: str = ""
    amount_paid: float = 0.0
    remaining_amount: float = 0.0
    payment_notes: str = ""
    created_at: datetime
    order_date: datetime
    items: List[OrderItemResponse]
    
    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "admin"

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class AuditLogResponse(BaseModel):
    id: int
    username: str
    action: str
    entity: str
    entity_id: str
    details: str
    created_at: datetime

    if hasattr(BaseModel, "model_config"):
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            from_attributes = True

# ========== FASTAPI APP ==========
app = FastAPI(title="Pharmacy Management System", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_order_number():
    return f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

def get_product_price(product, item_price, item_unit_price):
    if item_price is not None:
        return float(item_price)
    if item_unit_price is not None:
        return float(item_unit_price)
    return float(product.unit_price)


def log_action(db: Session, action: str, entity: str = "", entity_id: str = "", details: str = "", username: str = "system"):
    """Persist a lightweight audit log entry without interrupting the user action."""
    try:
        db.add(AuditLog(
            username=username or "system",
            action=action,
            entity=entity or "",
            entity_id=str(entity_id or ""),
            details=str(details or "")[:1000],
        ))
    except Exception as exc:
        logger.warning(f"Could not write audit log: {exc}")


def add_order_history(db: Session, order_id: int, old_status: str, new_status: str, note: str = ""):
    try:
        db.add(OrderStatusHistory(
            order_id=order_id,
            old_status=old_status or "",
            new_status=new_status or "",
            note=note or "",
        ))
    except Exception as exc:
        logger.warning(f"Could not write order history: {exc}")

def calculate_final_total(total_amount: float, discount: float = 0.0, discount_type: str = "value") -> float:
    try:
        total_amount = float(total_amount or 0.0)
        discount = max(float(discount or 0.0), 0.0)
    except (TypeError, ValueError):
        return float(total_amount or 0.0)
    
    if str(discount_type).lower() in ("percent", "percentage", "%"):
        discount_value = total_amount * min(discount, 100.0) / 100.0
    else:
        discount_value = min(discount, total_amount)
    
    return max(total_amount - discount_value, 0.0)

def load_app_settings():
    try:
        with open("app_settings.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}

def is_whatsapp_notifications_enabled():
    return bool(load_app_settings().get("whatsapp_order_notifications", False))

def normalize_phone(phone):
    return "".join(ch for ch in str(phone or "") if ch.isdigit())

def open_whatsapp_message(phone, message):
    clean_phone = normalize_phone(phone)
    if not clean_phone:
        return False
    url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(message)}"
    try:
        webbrowser.open(url)
        return True
    except Exception as e:
        logger.warning(f"Could not open WhatsApp URL: {e}")
        return False


def get_product_category_name(product):
    if getattr(product, "category_obj", None):
        return product.category_obj.name
    return product.category or "عام"


def normalize_product_images(images=None, product_images_json=None, image_url=None, image_path=None):
    result = []
    if isinstance(images, list):
        result.extend(images)
    elif isinstance(images, str) and images.strip():
        result.append(images)
    if product_images_json:
        try:
            parsed = json.loads(product_images_json)
            if isinstance(parsed, list):
                result.extend(parsed)
            elif isinstance(parsed, str) and parsed.strip():
                result.append(parsed)
        except Exception:
            if str(product_images_json).strip():
                result.append(str(product_images_json).strip())
    for legacy in (image_url, image_path):
        legacy = (legacy or "").strip()
        if legacy:
            result.append(legacy)

    cleaned = []
    seen = set()
    for item in result:
        item = str(item or "").strip()
        if item and item not in seen:
            cleaned.append(item)
            seen.add(item)
    return cleaned


def get_product_images(product):
    return normalize_product_images(
        product_images_json=getattr(product, "product_images_json", ""),
        image_url=getattr(product, "image_url", ""),
        image_path=getattr(product, "image_path", ""),
    )


def build_product_response(product):
    images = get_product_images(product)
    return ProductResponse(
        id=product.id,
        name=product.name,
        price=product.unit_price,
        unit_price=product.unit_price,
        quantity=product.quantity,
        expiry_date=product.expiry_date,
        barcode=product.barcode,
        category=product.category,
        category_id=product.category_id,
        category_name=get_product_category_name(product),
        company=product.company,
        image_path=product.image_path,
        image_url=product.image_url or (images[0] if images else None),
        images=images,
        product_images_json=product.product_images_json or "",
        description=product.description or "",
        is_active=int(product.is_active if product.is_active is not None else 1),
        created_at=product.created_at,
        updated_at=product.updated_at
    )


def normalize_pharmacy_account_status(value: Optional[str]) -> str:
    value = (value or "active").strip().lower()
    if value not in {"pending", "active", "blocked", "deleted"}:
        return "active"
    return value


def ensure_pharmacy_is_active(pharmacy: Pharmacy):
    status_value = normalize_pharmacy_account_status(getattr(pharmacy, "account_status", None))
    if status_value == "active":
        return
    if status_value == "pending":
        raise HTTPException(status_code=403, detail="Pharmacy account is pending approval")
    if status_value == "blocked":
        raise HTTPException(status_code=403, detail="Pharmacy account is blocked")
    raise HTTPException(status_code=403, detail="Pharmacy account is deleted")

# ========== HEALTH CHECK ==========
@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/auth/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username.strip()).first()
    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if user.password == credentials.password:
        user.password = hash_password(credentials.password)
    log_action(db, "login", "user", user.id, f"{user.username} logged in", user.username)
    db.commit()
    return {"id": user.id, "username": user.username, "role": user.role}

# ========== USERS API ==========
@app.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [UserResponse(id=u.id, username=u.username, role=u.role, created_at=u.created_at) for u in users]

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if not user.username or not user.username.strip():
        raise HTTPException(status_code=400, detail="Username is required")
    if not user.password:
        raise HTTPException(status_code=400, detail="Password is required")
    role = user.role if user.role in ("admin", "accountant", "rep") else "rep"
    existing = db.query(User).filter(User.username == user.username.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(username=user.username.strip(), password=hash_password(user.password), role=role)
    db.add(new_user)
    log_action(db, "create", "user", user.username.strip(), f"role={role}")
    db.commit()
    db.refresh(new_user)
    return UserResponse(id=new_user.id, username=new_user.username, role=new_user.role, created_at=new_user.created_at)

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete default admin")
    username = user.username
    db.delete(user)
    log_action(db, "delete", "user", user_id, username)
    db.commit()
    return {"message": "User deleted successfully"}


@app.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    limit = max(1, min(int(limit or 100), 500))
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return logs


# ========== CATEGORIES API ==========
@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.name.asc()).all()
    return [
        CategoryResponse(
            id=category.id,
            name=category.name,
            created_at=category.created_at,
            product_count=db.query(Product).filter(Product.category_id == category.id).count()
        )
        for category in categories
    ]


@app.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    name = (category.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    new_category = Category(name=name)
    db.add(new_category)
    log_action(db, "create", "category", name, "")
    db.commit()
    db.refresh(new_category)
    return CategoryResponse(id=new_category.id, name=new_category.name, created_at=new_category.created_at, product_count=0)


@app.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, category: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.id == category_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    name = (category.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")
    conflict = db.query(Category).filter(Category.name == name, Category.id != category_id).first()
    if conflict:
        raise HTTPException(status_code=400, detail="Category already exists")
    old_name = existing.name
    existing.name = name
    db.query(Product).filter(Product.category_id == category_id).update({"category": name})
    log_action(db, "update", "category", category_id, f"{old_name} -> {name}")
    db.commit()
    db.refresh(existing)
    count = db.query(Product).filter(Product.category_id == existing.id).count()
    return CategoryResponse(id=existing.id, name=existing.name, created_at=existing.created_at, product_count=count)


@app.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    linked_products = db.query(Product).filter(Product.category_id == category_id).count()
    if linked_products:
        raise HTTPException(status_code=400, detail="Cannot delete category because it is linked to products")
    name = category.name
    db.delete(category)
    log_action(db, "delete", "category", category_id, name)
    db.commit()
    return {"message": "Category deleted successfully"}


# ========== SUPPLIERS & PURCHASES API ==========
def build_supplier_response(supplier: Supplier) -> SupplierResponse:
    return SupplierResponse(
        id=supplier.id,
        name=supplier.name,
        phone=supplier.phone or "",
        address=supplier.address or "",
        company=supplier.company or "",
        balance=float(supplier.balance or 0.0),
        notes=supplier.notes or "",
        purchases_count=len(supplier.purchases or []),
        created_at=supplier.created_at or datetime.now(),
    )


def build_purchase_response(purchase: Purchase) -> PurchaseResponse:
    return PurchaseResponse(
        id=purchase.id,
        invoice_number=purchase.invoice_number,
        supplier_id=purchase.supplier_id,
        supplier_name=purchase.supplier.name if purchase.supplier else "",
        total_amount=float(purchase.total_amount or 0.0),
        amount_paid=float(purchase.amount_paid or 0.0),
        remaining_amount=float(purchase.remaining_amount or 0.0),
        status=purchase.status or "unpaid",
        notes=purchase.notes or "",
        created_at=purchase.created_at or datetime.now(),
        items=[
            PurchaseItemResponse(
                product_id=item.product_id,
                product_name=item.product.name if item.product else "",
                quantity=int(item.quantity or 0),
                unit_cost=float(item.unit_cost or 0.0),
                total_cost=float(item.total_cost or 0.0),
            )
            for item in (purchase.items or [])
        ],
    )


@app.get("/suppliers", response_model=List[SupplierResponse])
def get_suppliers(db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).order_by(Supplier.created_at.desc()).all()
    return [build_supplier_response(supplier) for supplier in suppliers]


@app.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    name = (supplier.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Supplier name is required")
    new_supplier = Supplier(
        name=name,
        phone=(supplier.phone or "").strip(),
        address=(supplier.address or "").strip(),
        company=(supplier.company or "").strip(),
        balance=float(supplier.balance or 0.0),
        notes=(supplier.notes or "").strip(),
        created_at=datetime.now(),
    )
    db.add(new_supplier)
    log_action(db, "create", "supplier", name, "")
    db.commit()
    db.refresh(new_supplier)
    return build_supplier_response(new_supplier)


@app.put("/suppliers/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: int, supplier: SupplierCreate, db: Session = Depends(get_db)):
    existing = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Supplier not found")
    name = (supplier.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Supplier name is required")
    existing.name = name
    existing.phone = (supplier.phone or "").strip()
    existing.address = (supplier.address or "").strip()
    existing.company = (supplier.company or "").strip()
    existing.balance = float(supplier.balance or 0.0)
    existing.notes = (supplier.notes or "").strip()
    log_action(db, "update", "supplier", supplier_id, name)
    db.commit()
    db.refresh(existing)
    return build_supplier_response(existing)


@app.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    purchases_count = db.query(Purchase).filter(Purchase.supplier_id == supplier_id).count()
    if purchases_count:
        raise HTTPException(status_code=400, detail="Cannot delete supplier linked to purchases")
    db.delete(supplier)
    log_action(db, "delete", "supplier", supplier_id, supplier.name)
    db.commit()
    return {"message": "Supplier deleted successfully"}


@app.get("/purchases", response_model=List[PurchaseResponse])
def get_purchases(supplier_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Purchase)
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)
    purchases = query.order_by(Purchase.created_at.desc()).all()
    return [build_purchase_response(purchase) for purchase in purchases]


@app.post("/purchases", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
def create_purchase(purchase: PurchaseCreate, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == purchase.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if not purchase.items:
        raise HTTPException(status_code=400, detail="Purchase must contain at least one item")

    prepared_items = []
    total_amount = 0.0
    for item in purchase.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        quantity = int(item.quantity or 0)
        unit_cost = float(item.unit_cost or 0.0)
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
        if unit_cost < 0:
            raise HTTPException(status_code=400, detail="Unit cost cannot be negative")
        total_cost = quantity * unit_cost
        total_amount += total_cost
        prepared_items.append((product, quantity, unit_cost, total_cost))

    amount_paid = max(float(purchase.amount_paid or 0.0), 0.0)
    if amount_paid > total_amount:
        raise HTTPException(status_code=400, detail="Paid amount cannot exceed purchase total")
    remaining_amount = round(total_amount - amount_paid, 2)
    if amount_paid <= 0:
        purchase_status = "unpaid"
    elif remaining_amount <= 0:
        purchase_status = "paid"
    else:
        purchase_status = "partial"

    invoice_number = (purchase.invoice_number or "").strip()
    if not invoice_number:
        invoice_number = f"PUR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    if db.query(Purchase).filter(Purchase.invoice_number == invoice_number).first():
        raise HTTPException(status_code=400, detail="Invoice number already exists")

    new_purchase = Purchase(
        invoice_number=invoice_number,
        supplier_id=supplier.id,
        total_amount=round(total_amount, 2),
        amount_paid=round(amount_paid, 2),
        remaining_amount=remaining_amount,
        status=purchase_status,
        notes=(purchase.notes or "").strip(),
        created_at=datetime.now(),
    )
    db.add(new_purchase)
    db.flush()

    for product, quantity, unit_cost, total_cost in prepared_items:
        product.quantity = int(product.quantity or 0) + quantity
        product.updated_at = datetime.now()
        db.add(PurchaseItem(
            purchase_id=new_purchase.id,
            product_id=product.id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=round(total_cost, 2),
        ))

    supplier.balance = float(supplier.balance or 0.0) + remaining_amount
    log_action(db, "create", "purchase", invoice_number, f"supplier={supplier.name}, total={total_amount}")
    db.commit()
    db.refresh(new_purchase)
    return build_purchase_response(new_purchase)

# ========== PRODUCTS API ==========
@app.get("/products", response_model=List[ProductResponse])
def get_products(search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Product)
    if search:
        query = query.filter(Product.name.contains(search))
    products = query.all()
    
    return [build_product_response(p) for p in products]

@app.get("/client/products")
def get_client_products(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active == 1).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "unit_price": p.unit_price,
            "price": p.unit_price,
            "quantity": p.quantity,
            "category": get_product_category_name(p),
            "company": p.company,
            "expiry_date": p.expiry_date,
            "image_url": p.image_url or (get_product_images(p)[0] if get_product_images(p) else None),
            "images": get_product_images(p),
            "description": p.description or "",
            "available": (p.quantity or 0) > 0,
        }
        for p in products
    ]

@app.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    if not product.name or not product.name.strip():
        raise HTTPException(status_code=400, detail="Product name is required")
    
    if product.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity must be >= 0")
    
    final_price = product.price if product.price is not None else (product.unit_price or 0.0)
    if final_price < 0:
        raise HTTPException(status_code=400, detail="Price must be >= 0")
    
    final_barcode = product.barcode or f"AUTO-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
    existing_barcode = db.query(Product).filter(Product.barcode == final_barcode).first()
    if existing_barcode:
        raise HTTPException(status_code=400, detail="Barcode already exists")

    selected_category = None
    if product.category_id is not None:
        selected_category = db.query(Category).filter(Category.id == product.category_id).first()
        if not selected_category:
            raise HTTPException(status_code=404, detail="Category not found")
    category_name = selected_category.name if selected_category else (product.category or "عام")
    images = normalize_product_images(
        images=product.images,
        product_images_json=product.product_images_json,
        image_url=product.image_url,
        image_path=product.image_path,
    )
    
    new_product = Product(
        name=product.name.strip(),
        barcode=final_barcode,
        category=category_name,
        category_id=selected_category.id if selected_category else None,
        company=product.company or "غير محدد",
        quantity=int(product.quantity),
        unit_price=float(final_price),
        expiry_date=product.expiry_date,
        image_path=product.image_path,
        image_url=product.image_url or (images[0] if images else None),
        product_images_json=json.dumps(images, ensure_ascii=False),
        description=(product.description or "").strip(),
        is_active=1 if int(product.is_active if product.is_active is not None else 1) == 1 else 0
    )
    
    db.add(new_product)
    log_action(db, "create", "product", new_product.name, f"quantity={new_product.quantity}, price={new_product.unit_price}")
    db.commit()
    db.refresh(new_product)
    
    return build_product_response(new_product)

@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    existing_product = db.query(Product).filter(Product.id == product_id).first()
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.name or not product.name.strip():
        raise HTTPException(status_code=400, detail="Product name is required")
    
    if product.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity must be >= 0")
    
    final_price = product.price if product.price is not None else (product.unit_price or 0.0)
    if final_price < 0:
        raise HTTPException(status_code=400, detail="Price must be >= 0")
    
    final_barcode = product.barcode or f"AUTO-{product_id}"
    
    barcode_conflict = db.query(Product).filter(Product.barcode == final_barcode, Product.id != product_id).first()
    if barcode_conflict:
        raise HTTPException(status_code=400, detail="Barcode already exists on another product")

    selected_category = None
    if product.category_id is not None:
        selected_category = db.query(Category).filter(Category.id == product.category_id).first()
        if not selected_category:
            raise HTTPException(status_code=404, detail="Category not found")
    category_name = selected_category.name if selected_category else (product.category or existing_product.category or "عام")
    images = normalize_product_images(
        images=product.images,
        product_images_json=product.product_images_json,
        image_url=product.image_url,
        image_path=product.image_path,
    )
    
    existing_product.name = product.name.strip()
    existing_product.barcode = final_barcode
    existing_product.category = category_name
    existing_product.category_id = selected_category.id if selected_category else product.category_id
    existing_product.company = product.company or "غير محدد"
    existing_product.quantity = int(product.quantity)
    existing_product.unit_price = float(final_price)
    existing_product.expiry_date = product.expiry_date
    existing_product.image_path = product.image_path
    existing_product.image_url = product.image_url or (images[0] if images else None)
    existing_product.product_images_json = json.dumps(images, ensure_ascii=False)
    existing_product.description = (product.description or "").strip()
    existing_product.is_active = 1 if int(product.is_active if product.is_active is not None else 1) == 1 else 0
    existing_product.updated_at = datetime.now()
    log_action(db, "update", "product", product_id, existing_product.name)
    
    db.commit()
    db.refresh(existing_product)
    
    return build_product_response(existing_product)

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    order_items = db.query(OrderItem).filter(OrderItem.product_id == product_id).first()
    if order_items:
        raise HTTPException(status_code=400, detail="Cannot delete product because it is linked to existing orders")
    
    product_name = product.name
    db.delete(product)
    log_action(db, "delete", "product", product_id, product_name)
    db.commit()
    
    return {"message": "Product deleted successfully"}

# ========== PHARMACIES API ==========
@app.get("/pharmacies", response_model=List[PharmacyResponse])
def get_pharmacies(db: Session = Depends(get_db)):
    pharmacies = db.query(Pharmacy).all()
    return [PharmacyResponse(
        id=p.id,
        name=p.name,
        address=p.address,
        phone=p.phone,
        balance=p.balance,
        created_at=p.created_at,
        account_status=normalize_pharmacy_account_status(getattr(p, "account_status", None)),
        approved_at=getattr(p, "approved_at", None),
        blocked_at=getattr(p, "blocked_at", None),
        last_login_at=getattr(p, "last_login_at", None),
        device_id=getattr(p, "device_id", None),
    ) for p in pharmacies]

@app.post("/pharmacies", response_model=PharmacyResponse, status_code=status.HTTP_201_CREATED)
def create_pharmacy(pharmacy: PharmacyCreate, db: Session = Depends(get_db)):
    if not pharmacy.name or not pharmacy.name.strip():
        raise HTTPException(status_code=400, detail="Pharmacy name is required")
    if not pharmacy.address or not pharmacy.address.strip():
        raise HTTPException(status_code=400, detail="Pharmacy address is required")
    if not pharmacy.phone or not pharmacy.phone.strip():
        raise HTTPException(status_code=400, detail="Pharmacy phone is required")
    
    new_pharmacy = Pharmacy(
        name=pharmacy.name.strip(),
        address=pharmacy.address.strip(),
        phone=pharmacy.phone.strip(),
        balance=pharmacy.balance,
        account_status="pending",
    )
    
    db.add(new_pharmacy)
    log_action(db, "create", "pharmacy", new_pharmacy.name, f"balance={new_pharmacy.balance}")
    db.commit()
    db.refresh(new_pharmacy)
    
    return PharmacyResponse(
        id=new_pharmacy.id,
        name=new_pharmacy.name,
        address=new_pharmacy.address,
        phone=new_pharmacy.phone,
        balance=new_pharmacy.balance,
        created_at=new_pharmacy.created_at,
        account_status=normalize_pharmacy_account_status(getattr(new_pharmacy, "account_status", None)),
        approved_at=getattr(new_pharmacy, "approved_at", None),
        blocked_at=getattr(new_pharmacy, "blocked_at", None),
        last_login_at=getattr(new_pharmacy, "last_login_at", None),
        device_id=getattr(new_pharmacy, "device_id", None),
    )

@app.put("/pharmacies/{pharmacy_id}", response_model=PharmacyResponse)
def update_pharmacy(pharmacy_id: int, pharmacy: PharmacyCreate, db: Session = Depends(get_db)):
    existing_pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not existing_pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    
    if not pharmacy.name or not pharmacy.name.strip():
        raise HTTPException(status_code=400, detail="Pharmacy name is required")
    if not pharmacy.address or not pharmacy.address.strip():
        raise HTTPException(status_code=400, detail="Pharmacy address is required")
    if not pharmacy.phone or not pharmacy.phone.strip():
        raise HTTPException(status_code=400, detail="Pharmacy phone is required")
    
    existing_pharmacy.name = pharmacy.name.strip()
    existing_pharmacy.address = pharmacy.address.strip()
    existing_pharmacy.phone = pharmacy.phone.strip()
    existing_pharmacy.balance = pharmacy.balance
    log_action(db, "update", "pharmacy", pharmacy_id, existing_pharmacy.name)
    
    db.commit()
    db.refresh(existing_pharmacy)
    
    return PharmacyResponse(
        id=existing_pharmacy.id,
        name=existing_pharmacy.name,
        address=existing_pharmacy.address,
        phone=existing_pharmacy.phone,
        balance=existing_pharmacy.balance,
        created_at=existing_pharmacy.created_at,
        account_status=normalize_pharmacy_account_status(getattr(existing_pharmacy, "account_status", None)),
        approved_at=getattr(existing_pharmacy, "approved_at", None),
        blocked_at=getattr(existing_pharmacy, "blocked_at", None),
        last_login_at=getattr(existing_pharmacy, "last_login_at", None),
        device_id=getattr(existing_pharmacy, "device_id", None),
    )

@app.delete("/pharmacies/{pharmacy_id}")
def delete_pharmacy(pharmacy_id: int, db: Session = Depends(get_db)):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    pharmacy_name = pharmacy.name
    pharmacy.account_status = "deleted"
    pharmacy.blocked_at = datetime.now()
    log_action(db, "revoke_access", "pharmacy", pharmacy_id, f"deleted (soft) {pharmacy_name}")
    db.commit()
    return {"message": "Pharmacy access revoked (deleted)"}


@app.put("/pharmacies/{pharmacy_id}/approve")
def approve_pharmacy_account(pharmacy_id: int, payload: PharmacyAccountAction = None, db: Session = Depends(get_db)):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    previous = normalize_pharmacy_account_status(getattr(pharmacy, "account_status", None))
    pharmacy.account_status = "active"
    pharmacy.approved_at = datetime.now()
    pharmacy.blocked_at = None
    note = (payload.note if payload else "") or ""
    log_action(db, "approve", "pharmacy", pharmacy_id, f"{previous} -> active. {note}".strip())
    db.commit()
    return {"message": "Pharmacy approved", "id": pharmacy_id, "account_status": "active"}


@app.put("/pharmacies/{pharmacy_id}/block")
def block_pharmacy_account(pharmacy_id: int, payload: PharmacyAccountAction = None, db: Session = Depends(get_db)):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    previous = normalize_pharmacy_account_status(getattr(pharmacy, "account_status", None))
    pharmacy.account_status = "blocked"
    pharmacy.blocked_at = datetime.now()
    note = (payload.note if payload else "") or ""
    log_action(db, "block", "pharmacy", pharmacy_id, f"{previous} -> blocked. {note}".strip())
    db.commit()
    return {"message": "Pharmacy blocked", "id": pharmacy_id, "account_status": "blocked"}


@app.put("/pharmacies/{pharmacy_id}/revoke")
def revoke_pharmacy_account(pharmacy_id: int, payload: PharmacyAccountAction = None, db: Session = Depends(get_db)):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    previous = normalize_pharmacy_account_status(getattr(pharmacy, "account_status", None))
    pharmacy.account_status = "deleted"
    pharmacy.blocked_at = datetime.now()
    note = (payload.note if payload else "") or ""
    log_action(db, "revoke_access", "pharmacy", pharmacy_id, f"{previous} -> deleted. {note}".strip())
    db.commit()
    return {"message": "Pharmacy access revoked", "id": pharmacy_id, "account_status": "deleted"}


@app.put("/pharmacies/{pharmacy_id}/reset-device")
def reset_pharmacy_device(pharmacy_id: int, db: Session = Depends(get_db)):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    pharmacy.device_id = None
    log_action(db, "reset_device", "pharmacy", pharmacy_id, "device_id cleared")
    db.commit()
    return {"message": "Device binding reset", "id": pharmacy_id}

# ========== ORDERS API ==========
@app.get("/orders", response_model=List[OrderResponse])
def get_orders(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Order)
    normalized_status_filter = None
    if status:
        normalized_status_filter = normalize_order_status(status)
        if normalized_status_filter not in VALID_ORDER_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(VALID_ORDER_STATUSES)}"
            )
    
    orders = query.all()
    if normalized_status_filter:
        orders = [order for order in orders if normalize_order_status(order.status) == normalized_status_filter]
    result = []
    
    for order in orders:
        pharmacy = db.query(Pharmacy).filter(Pharmacy.id == order.pharmacy_id).first()
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        display_status = normalize_order_status(order.status)
        
        items_response = []
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            items_response.append(OrderItemResponse(
                product_id=item.product_id,
                product_name=product.name if product else "Unknown",
                quantity=item.quantity,
                price=item.unit_price,
                unit_price=item.unit_price,
                total=item.total_price,
                total_price=item.total_price
            ))
        
        result.append(OrderResponse(
            id=order.id,
            order_number=order.order_number,
            pharmacy_id=order.pharmacy_id,
            pharmacy_name=pharmacy.name if pharmacy else "Unknown",
            total=order.final_total or order.total_amount,
            total_amount=order.total_amount,
            total_price=order.final_total or order.total_amount,
            discount=order.discount or 0.0,
            discount_type=order.discount_type or "value",
            final_total=order.final_total or order.total_amount,
            status=display_status,
            delivery_person=order.delivery_person or "",
            notes=order.notes or "",
            last_status_update=order.last_status_update,
            expected_delivery_note=order.expected_delivery_note or "",
            payment_status=order.payment_status or "unpaid",
            payment_type=order.payment_type or "",
            amount_paid=float(order.amount_paid or 0.0),
            remaining_amount=float(order.remaining_amount if order.remaining_amount is not None else (order.final_total or order.total_amount or 0.0)),
            payment_notes=order.payment_notes or "",
            created_at=order.created_at,
            order_date=order.created_at,
            items=items_response
        ))
    
    return result

@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == order_data.pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    ensure_pharmacy_is_active(pharmacy)
    
    if not order_data.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")
    
    total_amount = 0.0
    items_to_create = []
    
    for item_data in order_data.items:
        if item_data.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
        
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with id {item_data.product_id} not found")
        
        unit_price = get_product_price(product, item_data.price, item_data.unit_price)
        item_total = unit_price * item_data.quantity
        total_amount += item_total
        
        items_to_create.append({
            "product_id": product.id,
            "quantity": item_data.quantity,
            "unit_price": unit_price,
            "total_price": item_total
        })
    
    discount_type = (order_data.discount_type or "value").lower()
    if discount_type not in ("value", "percent", "percentage", "%"):
        discount_type = "value"
    final_total = calculate_final_total(total_amount, order_data.discount, discount_type)
    
    new_order = Order(
        order_number=generate_order_number(),
        pharmacy_id=order_data.pharmacy_id,
        total_amount=total_amount,
        discount=float(order_data.discount or 0.0),
        discount_type=discount_type,
        final_total=final_total,
        balance_before=pharmacy.balance,
        balance_after=pharmacy.balance,
        status="pending",
        delivery_person=(order_data.delivery_person or "").strip(),
        notes=(order_data.notes or "").strip(),
        expected_delivery_note=(order_data.expected_delivery_note or "").strip(),
        payment_status="unpaid",
        payment_type="",
        amount_paid=0.0,
        remaining_amount=final_total,
        payment_notes="",
        last_status_update=datetime.now()
    )
    
    db.add(new_order)
    db.flush()
    log_action(db, "create", "order", new_order.id, f"{new_order.order_number} total={new_order.final_total}")
    add_order_history(db, new_order.id, "", "pending", "Order created")
    
    for item in items_to_create:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item["product_id"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            total_price=item["total_price"]
        )
        db.add(order_item)
    
    db.commit()
    
    return {
        "id": new_order.id,
        "order_number": new_order.order_number,
        "status": new_order.status,
        "total": new_order.final_total,
        "total_amount": new_order.total_amount,
        "discount": new_order.discount,
        "discount_type": new_order.discount_type,
        "final_total": new_order.final_total,
        "delivery_person": new_order.delivery_person or "",
        "notes": new_order.notes or "",
        "last_status_update": new_order.last_status_update,
        "expected_delivery_note": new_order.expected_delivery_note or ""
    }

@app.get("/invoices/{order_id}/pdf")
def download_order_invoice_pdf(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == order.pharmacy_id).first()
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except Exception:
        raise HTTPException(status_code=500, detail="reportlab is required to generate invoices")

    invoices_dir = os.path.join(os.getcwd(), "generated_invoices")
    os.makedirs(invoices_dir, exist_ok=True)
    invoice_number = order.order_number or f"ORD-{order.id}"
    file_path = os.path.join(invoices_dir, f"invoice_{order.id}.pdf")

    styles = getSampleStyleSheet()
    story = [
        Paragraph("Al Nada Pharmacy Store", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Invoice: {invoice_number}", styles["Heading2"]),
        Paragraph(f"Pharmacy: {pharmacy.name if pharmacy else 'Unknown'}", styles["Normal"]),
        Paragraph(f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else '-'}", styles["Normal"]),
        Paragraph(f"Status: {order.status}", styles["Normal"]),
        Spacer(1, 12),
    ]

    table_data = [["Product", "Quantity", "Unit Price", "Total"]]
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        table_data.append([
            product.name if product else f"Product #{item.product_id}",
            str(item.quantity),
            f"{float(item.unit_price or 0):.2f}",
            f"{float(item.total_price or 0):.2f}",
        ])

    table_data.append(["", "", "Total", f"{float(order.final_total or order.total_amount or 0):.2f}"])
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(table)

    SimpleDocTemplate(file_path, pagesize=A4).build(story)
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"{invoice_number}.pdf",
    )
@app.put("/orders/{order_id}")
def update_order(order_id: int, order_data: OrderCreate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    current_status = normalize_order_status(order.status)
    if current_status in (OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value):
        raise HTTPException(status_code=400, detail="Delivered or cancelled orders cannot be edited")
    if current_status != OrderStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Only pending orders can be edited")
    
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == order_data.pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    if not order_data.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")
    
    total_amount = 0.0
    items_to_create = []
    
    for item_data in order_data.items:
        if item_data.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with id {item_data.product_id} not found")
        unit_price = get_product_price(product, item_data.price, item_data.unit_price)
        item_total = unit_price * item_data.quantity
        total_amount += item_total
        items_to_create.append({
            "product_id": product.id,
            "quantity": item_data.quantity,
            "unit_price": unit_price,
            "total_price": item_total
        })
    
    discount_type = (order_data.discount_type or "value").lower()
    if discount_type not in ("value", "percent", "percentage", "%"):
        discount_type = "value"
    final_total = calculate_final_total(total_amount, order_data.discount, discount_type)
    
    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
    order.pharmacy_id = order_data.pharmacy_id
    order.total_amount = total_amount
    order.discount = float(order_data.discount or 0.0)
    order.discount_type = discount_type
    order.final_total = final_total
    order.balance_before = pharmacy.balance
    order.balance_after = pharmacy.balance
    order.delivery_person = (order_data.delivery_person or "").strip()
    order.notes = (order_data.notes or "").strip()
    order.expected_delivery_note = (order_data.expected_delivery_note or "").strip()
    
    for item in items_to_create:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item["product_id"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            total_price=item["total_price"]
        ))
    log_action(db, "update", "order", order.id, f"{order.order_number} total={order.final_total}")
    
    db.commit()
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "total": order.final_total,
        "total_amount": order.total_amount,
        "discount": order.discount,
        "discount_type": order.discount_type,
        "final_total": order.final_total,
        "delivery_person": order.delivery_person or "",
        "notes": order.notes or "",
        "last_status_update": order.last_status_update,
        "expected_delivery_note": order.expected_delivery_note or ""
    }

@app.put("/orders/{order_id}/status")
def update_order_status(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    new_status = normalize_order_status(status_update.status)
    if new_status not in VALID_ORDER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {', '.join(VALID_ORDER_STATUSES)}"
        )

    current_status = normalize_order_status(order.status)
    allowed_transitions = {
        OrderStatus.PENDING.value: {OrderStatus.REVIEWED.value, OrderStatus.POSTPONED.value, OrderStatus.CANCELLED.value},
        OrderStatus.REVIEWED.value: {OrderStatus.IN_STORE.value, OrderStatus.POSTPONED.value, OrderStatus.CANCELLED.value},
        OrderStatus.IN_STORE.value: {OrderStatus.WITH_DRIVER.value, OrderStatus.POSTPONED.value, OrderStatus.CANCELLED.value},
        OrderStatus.WITH_DRIVER.value: {OrderStatus.ON_THE_WAY.value, OrderStatus.POSTPONED.value, OrderStatus.CANCELLED.value},
        OrderStatus.ON_THE_WAY.value: {OrderStatus.DELIVERED.value, OrderStatus.POSTPONED.value, OrderStatus.CANCELLED.value},
        OrderStatus.POSTPONED.value: {OrderStatus.REVIEWED.value, OrderStatus.IN_STORE.value, OrderStatus.WITH_DRIVER.value, OrderStatus.ON_THE_WAY.value, OrderStatus.CANCELLED.value},
        OrderStatus.DELIVERED.value: set(),
        OrderStatus.CANCELLED.value: set(),
    }

    if new_status == current_status:
        return {"status": normalize_order_status(order.status)}

    if new_status not in allowed_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update order status from {current_status} to {new_status}"
        )
    
    if status_update.delivery_person is not None:
        order.delivery_person = status_update.delivery_person.strip()
    if status_update.notes is not None:
        order.notes = status_update.notes.strip()
    if status_update.expected_delivery_note is not None:
        order.expected_delivery_note = status_update.expected_delivery_note.strip()

    if current_status == OrderStatus.PENDING.value and new_status == OrderStatus.REVIEWED.value:
        pharmacy = db.query(Pharmacy).filter(Pharmacy.id == order.pharmacy_id).first()
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        for item in order_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product.quantity < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for product: {product.name}. Available: {product.quantity}, Requested: {item.quantity}")
        
        for item in order_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            product.quantity -= item.quantity
        
        charged_total = order.final_total or order.total_amount
        order.balance_before = pharmacy.balance
        pharmacy.balance += charged_total
        order.balance_after = pharmacy.balance
        order.status = OrderStatus.REVIEWED.value
        if is_whatsapp_notifications_enabled():
            message = (
                f"📋 تمت مراجعة طلبك رقم {order.order_number} بقيمة "
                f"{charged_total:.2f} جنيه. شكراً للتعامل مع مخزن الندا."
            )
            open_whatsapp_message(pharmacy.phone, message)
    else:
        order.status = new_status

    order.last_status_update = datetime.now()
    if order.status == OrderStatus.ON_THE_WAY.value and not (order.expected_delivery_note or "").strip():
        order.expected_delivery_note = DEFAULT_ON_THE_WAY_NOTE
    
    log_action(db, "status_change", "order", order.id, f"{current_status} -> {order.status}")
    add_order_history(db, order.id, current_status, order.status, "Status updated")
    
    db.commit()
    
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": normalize_order_status(order.status),
        "delivery_person": order.delivery_person or "",
        "notes": order.notes or "",
        "last_status_update": order.last_status_update,
        "expected_delivery_note": order.expected_delivery_note or "",
    }

# ========== PAYMENTS API ==========
@app.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == payment.pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    payment_type = (payment.payment_type or "cash").lower()
    if payment_type not in VALID_PAYMENT_TYPES:
        payment_type = "cash"

    amount = float(payment.amount or 0.0)
    if amount < 0:
        raise HTTPException(status_code=400, detail="Payment amount cannot be negative")
    if payment_type not in ("deferred", "collect_on_delivery") and amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")

    order = None
    total_due = float(pharmacy.balance or 0.0)
    already_paid = 0.0
    if payment.order_id:
        order = db.query(Order).filter(Order.id == payment.order_id, Order.pharmacy_id == payment.pharmacy_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found for this pharmacy")
        normalized_order_status = normalize_order_status(order.status)
        if payment_type == "collect_on_delivery" and normalized_order_status not in {
            OrderStatus.WITH_DRIVER.value,
            OrderStatus.ON_THE_WAY.value,
            OrderStatus.DELIVERED.value,
        }:
            raise HTTPException(
                status_code=400,
                detail="collect_on_delivery is only allowed when order is with_driver, on_the_way, or delivered"
            )
        order_total = float(order.final_total or order.total_amount or 0.0)
        already_paid = float(order.amount_paid or 0.0)
        total_due = max(order_total - already_paid, 0.0)
        if total_due <= 0:
            raise HTTPException(status_code=400, detail="Order is already fully paid")

    if amount > total_due + 0.0001:
        raise HTTPException(status_code=400, detail=f"Payment amount exceeds due amount. Due: {total_due}")
    if amount > float(pharmacy.balance or 0.0) + 0.0001:
        raise HTTPException(status_code=400, detail=f"Payment amount exceeds pharmacy balance. Balance: {pharmacy.balance}")

    amount_after_payment = already_paid + amount if order else amount
    target_total = float(order.final_total or order.total_amount or 0.0) if order else float(pharmacy.balance or 0.0)
    remaining_amount = max(target_total - amount_after_payment, 0.0) if order else max(float(pharmacy.balance or 0.0) - amount, 0.0)
    payment_status = payment.payment_status or calculate_payment_status(amount_after_payment if order else amount, target_total, payment_type)
    if remaining_amount <= 0 and amount > 0:
        payment_status = "full"

    new_payment = Payment(
        pharmacy_id=payment.pharmacy_id,
        order_id=payment.order_id,
        amount=amount,
        payment_status=payment_status,
        payment_type=payment_type,
        amount_paid=amount,
        remaining_amount=remaining_amount,
        payment_notes=(payment.payment_notes or "").strip()
    )
    db.add(new_payment)

    if amount > 0:
        pharmacy.balance -= amount

    if order:
        order.amount_paid = amount_after_payment
        order.remaining_amount = remaining_amount
        order.payment_status = calculate_payment_status(order.amount_paid, float(order.final_total or order.total_amount or 0.0), payment_type)
        if payment_type in ("deferred", "collect_on_delivery") and amount <= 0:
            order.payment_status = payment_type
        elif order.remaining_amount <= 0:
            order.payment_status = "full"
        order.payment_type = payment_type
        order.payment_notes = (payment.payment_notes or "").strip()

    log_action(db, "create", "payment", pharmacy.id, f"amount={amount}, pharmacy={pharmacy.name}, order_id={payment.order_id or ''}")
    
    db.commit()
    db.refresh(new_payment)
    
    return {
        "id": new_payment.id,
        "pharmacy_id": new_payment.pharmacy_id,
        "order_id": new_payment.order_id,
        "amount": new_payment.amount,
        "payment_status": new_payment.payment_status or "partial",
        "payment_type": new_payment.payment_type or "cash",
        "amount_paid": new_payment.amount_paid or new_payment.amount,
        "remaining_amount": new_payment.remaining_amount or 0.0,
        "payment_notes": new_payment.payment_notes or "",
        "date": new_payment.date,
        "new_balance": pharmacy.balance,
    }

@app.get("/pharmacies/{pharmacy_id}/payments", response_model=List[PaymentResponse])
def get_pharmacy_payments(pharmacy_id: int, db: Session = Depends(get_db)):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    
    payments = db.query(Payment).filter(Payment.pharmacy_id == pharmacy_id).all()
    
    return [PaymentResponse(
        id=p.id,
        pharmacy_id=p.pharmacy_id,
        order_id=p.order_id,
        amount=p.amount,
        payment_status=p.payment_status or "partial",
        payment_type=p.payment_type or "cash",
        amount_paid=p.amount_paid or p.amount,
        remaining_amount=p.remaining_amount or 0.0,
        payment_notes=p.payment_notes or "",
        date=p.date
    ) for p in payments]


@app.get("/data/export")
def export_data(db: Session = Depends(get_db)):
    """Export core business data as JSON-friendly dictionaries."""
    products = db.query(Product).all()
    pharmacies = db.query(Pharmacy).all()
    orders = db.query(Order).all()
    order_items = db.query(OrderItem).all()
    payments = db.query(Payment).all()
    return {
        "exported_at": datetime.now().isoformat(),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "barcode": p.barcode,
                "category": p.category,
                "company": p.company,
                "quantity": p.quantity,
                "unit_price": p.unit_price,
                "expiry_date": p.expiry_date,
                "image_path": p.image_path,
            }
            for p in products
        ],
        "pharmacies": [
            {
                "id": p.id,
                "name": p.name,
                "address": p.address,
                "phone": p.phone,
                "balance": p.balance,
            }
            for p in pharmacies
        ],
        "orders": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "pharmacy_id": o.pharmacy_id,
                "total_amount": o.total_amount,
                "discount": o.discount,
                "discount_type": o.discount_type,
                "final_total": o.final_total,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
        "order_items": [
            {
                "order_id": item.order_id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
            }
            for item in order_items
        ],
        "payments": [
            {
                "id": p.id,
                "pharmacy_id": p.pharmacy_id,
                "amount": p.amount,
                "date": p.date.isoformat() if p.date else None,
            }
            for p in payments
        ],
    }


@app.post("/data/import")
def import_data(payload: dict, db: Session = Depends(get_db)):
    """Import products and pharmacies only when their IDs do not already exist."""
    created = {"products": 0, "pharmacies": 0}
    for item in payload.get("products", []):
        if db.query(Product).filter(Product.id == item.get("id")).first():
            continue
        product = Product(
            id=item.get("id"),
            name=item.get("name") or "Imported Product",
            barcode=item.get("barcode") or f"IMP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            category=item.get("category") or "عام",
            company=item.get("company") or "غير محدد",
            quantity=int(item.get("quantity") or 0),
            unit_price=float(item.get("unit_price") or 0),
            expiry_date=item.get("expiry_date"),
            image_path=item.get("image_path"),
        )
        db.add(product)
        created["products"] += 1
    for item in payload.get("pharmacies", []):
        if db.query(Pharmacy).filter(Pharmacy.id == item.get("id")).first():
            continue
        pharmacy = Pharmacy(
            id=item.get("id"),
            name=item.get("name") or "Imported Pharmacy",
            address=item.get("address") or "-",
            phone=item.get("phone") or "-",
            balance=float(item.get("balance") or 0),
        )
        db.add(pharmacy)
        created["pharmacies"] += 1
    log_action(db, "import", "data", "", json.dumps(created, ensure_ascii=False))
    db.commit()
    return {"message": "Import completed", "created": created}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
