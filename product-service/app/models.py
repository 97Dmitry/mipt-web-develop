from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, ForeignKey, Index,
    Integer, SmallInteger, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TIMESTAMP
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    products: Mapped[list["Product"]] = relationship("Product", back_populates="category")

    __table_args__ = (
        Index("ix_categories_is_active_sort", "is_active", "sort_order"),
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    base_type: Mapped[str] = mapped_column(String(20), nullable=False)
    wattage: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    color_temperature_k: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    luminous_flux_lm: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage", back_populates="product",
        cascade="all, delete-orphan", order_by="ProductImage.sort_order"
    )

    __table_args__ = (
        CheckConstraint("price_minor > 0", name="ck_products_price_minor"),
        CheckConstraint("stock_qty >= 0", name="ck_products_stock_qty"),
        CheckConstraint("wattage > 0", name="ck_products_wattage"),
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_is_active", "is_active"),
        Index("ix_products_price_minor", "price_minor"),
        Index("ix_products_stock_qty", "stock_qty"),
        Index("ix_products_base_type", "base_type"),
        Index("ix_products_catalog_filters", "category_id", "base_type", "wattage", "color_temperature_k", "is_active"),
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)

    product: Mapped["Product"] = relationship("Product", back_populates="images")

    __table_args__ = (
        Index("ix_product_images_product_id_sort", "product_id", "sort_order"),
    )
