from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Product(Base):
    """جدول الأصناف (الأدوية)"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    quantity = Column(Integer, default=0)
    price = Column(Float, nullable=False)
    expiry_date = Column(String, nullable=True)

class Pharmacy(Base):
    """جدول الصيدليات"""
    __tablename__ = "pharmacies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    balance = Column(Float, default=0.0)

    # العلاقات
    orders = relationship("Order", back_populates="pharmacy")
    payments = relationship("Payment", back_populates="pharmacy")

class Order(Base):
    """جدول الطلبيات"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"))
    total_price = Column(Float, default=0.0)
    status = Column(String, default="Pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # العلاقات
    pharmacy = relationship("Pharmacy", back_populates="orders")

class Payment(Base):
    """جدول التحصيلات المالية"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())

    # العلاقات
    pharmacy = relationship("Pharmacy", back_populates="payments")