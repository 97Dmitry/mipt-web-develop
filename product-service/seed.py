"""Seed script: creates schema and fills base catalog only when DB is empty."""

import asyncio
import os

from slugify import slugify
from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine
from app.models import Category, Product, ProductImage

# slug -> (name, sort_order)
CATEGORIES = [
    {"name": "Светодиодные стандартные", "slug": "led-standard", "sort_order": 1},
    {"name": "Светодиодные свечи", "slug": "led-candle", "sort_order": 2},
    {"name": "Споты GU10", "slug": "spot-gu10", "sort_order": 3},
    {"name": "Таблетки GX53", "slug": "gx53", "sort_order": 4},
    {"name": "Филаментные лампы", "slug": "filament", "sort_order": 5},
]

# category_slug used to look up actual DB id after insert
PRODUCTS = [
    {"sku": "STD-E27-07-30", "name": "LED A60 7Вт 3000K", "cat_slug": "led-standard", "base_type": "E27", "wattage": 7, "color_temperature_k": 3000, "luminous_flux_lm": 700, "price_minor": 14900, "stock_qty": 35},
    {"sku": "STD-E27-09-40", "name": "LED A60 9Вт 4000K", "cat_slug": "led-standard", "base_type": "E27", "wattage": 9, "color_temperature_k": 4000, "luminous_flux_lm": 900, "price_minor": 15900, "stock_qty": 42},
    {"sku": "STD-E27-12-65", "name": "LED A65 12Вт 6500K", "cat_slug": "led-standard", "base_type": "E27", "wattage": 12, "color_temperature_k": 6500, "luminous_flux_lm": 1200, "price_minor": 17900, "stock_qty": 28},
    {"sku": "STD-E27-15-40", "name": "LED A67 15Вт 4000K", "cat_slug": "led-standard", "base_type": "E27", "wattage": 15, "color_temperature_k": 4000, "luminous_flux_lm": 1500, "price_minor": 22900, "stock_qty": 18},
    {"sku": "CND-E14-05-27", "name": "LED Candle 5Вт 2700K", "cat_slug": "led-candle", "base_type": "E14", "wattage": 5, "color_temperature_k": 2700, "luminous_flux_lm": 450, "price_minor": 13900, "stock_qty": 30},
    {"sku": "CND-E14-07-40", "name": "LED Candle 7Вт 4000K", "cat_slug": "led-candle", "base_type": "E14", "wattage": 7, "color_temperature_k": 4000, "luminous_flux_lm": 620, "price_minor": 14900, "stock_qty": 24},
    {"sku": "CND-E14-07-65", "name": "LED Candle 7Вт 6500K", "cat_slug": "led-candle", "base_type": "E14", "wattage": 7, "color_temperature_k": 6500, "luminous_flux_lm": 620, "price_minor": 14900, "stock_qty": 16},
    {"sku": "CND-E14-09-27", "name": "LED Candle 9Вт 2700K", "cat_slug": "led-candle", "base_type": "E14", "wattage": 9, "color_temperature_k": 2700, "luminous_flux_lm": 800, "price_minor": 16900, "stock_qty": 12},
    {"sku": "SPT-GU10-05-30", "name": "LED Spot GU10 5Вт 3000K", "cat_slug": "spot-gu10", "base_type": "GU10", "wattage": 5, "color_temperature_k": 3000, "luminous_flux_lm": 420, "price_minor": 12900, "stock_qty": 44},
    {"sku": "SPT-GU10-07-40", "name": "LED Spot GU10 7Вт 4000K", "cat_slug": "spot-gu10", "base_type": "GU10", "wattage": 7, "color_temperature_k": 4000, "luminous_flux_lm": 560, "price_minor": 13900, "stock_qty": 40},
    {"sku": "SPT-GU10-07-65", "name": "LED Spot GU10 7Вт 6500K", "cat_slug": "spot-gu10", "base_type": "GU10", "wattage": 7, "color_temperature_k": 6500, "luminous_flux_lm": 560, "price_minor": 13900, "stock_qty": 21},
    {"sku": "SPT-GU10-09-30", "name": "LED Spot GU10 9Вт 3000K", "cat_slug": "spot-gu10", "base_type": "GU10", "wattage": 9, "color_temperature_k": 3000, "luminous_flux_lm": 800, "price_minor": 15900, "stock_qty": 8},
    {"sku": "G53-GX53-08-30", "name": "LED GX53 8Вт 3000K", "cat_slug": "gx53", "base_type": "GX53", "wattage": 8, "color_temperature_k": 3000, "luminous_flux_lm": 700, "price_minor": 11900, "stock_qty": 52},
    {"sku": "G53-GX53-10-40", "name": "LED GX53 10Вт 4000K", "cat_slug": "gx53", "base_type": "GX53", "wattage": 10, "color_temperature_k": 4000, "luminous_flux_lm": 900, "price_minor": 12900, "stock_qty": 47},
    {"sku": "G53-GX53-12-65", "name": "LED GX53 12Вт 6500K", "cat_slug": "gx53", "base_type": "GX53", "wattage": 12, "color_temperature_k": 6500, "luminous_flux_lm": 1050, "price_minor": 14900, "stock_qty": 32},
    {"sku": "G53-GX53-15-40", "name": "LED GX53 15Вт 4000K", "cat_slug": "gx53", "base_type": "GX53", "wattage": 15, "color_temperature_k": 4000, "luminous_flux_lm": 1350, "price_minor": 16900, "stock_qty": 14},
    {"sku": "FLM-E27-06-22", "name": "Filament A60 6Вт 2200K", "cat_slug": "filament", "base_type": "E27", "wattage": 6, "color_temperature_k": 2200, "luminous_flux_lm": 650, "price_minor": 19900, "stock_qty": 20},
    {"sku": "FLM-E27-08-27", "name": "Filament G95 8Вт 2700K", "cat_slug": "filament", "base_type": "E27", "wattage": 8, "color_temperature_k": 2700, "luminous_flux_lm": 820, "price_minor": 24900, "stock_qty": 15},
    {"sku": "FLM-E27-08-40", "name": "Filament ST64 8Вт 4000K", "cat_slug": "filament", "base_type": "E27", "wattage": 8, "color_temperature_k": 4000, "luminous_flux_lm": 820, "price_minor": 25900, "stock_qty": 11},
    {"sku": "FLM-E27-10-27", "name": "Filament Globe 10Вт 2700K", "cat_slug": "filament", "base_type": "E27", "wattage": 10, "color_temperature_k": 2700, "luminous_flux_lm": 1050, "price_minor": 29900, "stock_qty": 7},
]


def _enabled() -> bool:
    return os.environ.get("SEED_CATALOG_ON_START", "true").lower() in {"1", "true", "yes"}


async def _seed_empty_catalog() -> None:
    async with SessionLocal() as db:
        categories_total = (await db.execute(select(func.count()).select_from(Category))).scalar_one()
        products_total = (await db.execute(select(func.count()).select_from(Product))).scalar_one()

        if categories_total > 0 or products_total > 0:
            print(
                f"Seed skipped: catalog is not empty "
                f"(categories={categories_total}, products={products_total})."
            )
            return

        slug_to_id: dict[str, int] = {}
        for cat_data in CATEGORIES:
            category = Category(
                name=cat_data["name"],
                slug=cat_data["slug"],
                sort_order=cat_data["sort_order"],
            )
            db.add(category)
            await db.flush()
            slug_to_id[cat_data["slug"]] = category.id

        for prod_data in PRODUCTS:
            name = prod_data["name"]
            product = Product(
                sku=prod_data["sku"],
                name=name,
                slug=slugify(name),
                description=f"{name} — надёжная лампа для дома и офиса.",
                category_id=slug_to_id[prod_data["cat_slug"]],
                price_minor=prod_data["price_minor"],
                stock_qty=prod_data["stock_qty"],
                base_type=prod_data["base_type"],
                wattage=prod_data["wattage"],
                color_temperature_k=prod_data["color_temperature_k"],
                luminous_flux_lm=prod_data["luminous_flux_lm"],
                is_active=True,
            )
            db.add(product)
            await db.flush()
            db.add(
                ProductImage(
                    product_id=product.id,
                    image_url=f"https://cdn.example.com/products/{prod_data['sku'].lower()}/main.jpg",
                    alt_text=name,
                    sort_order=0,
                )
            )

        await db.commit()
        print(f"Seed completed: inserted {len(CATEGORIES)} categories and {len(PRODUCTS)} products.")


async def main() -> None:
    if not _enabled():
        print("Seed disabled by SEED_CATALOG_ON_START=false.")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_empty_catalog()


if __name__ == "__main__":
    asyncio.run(main())
