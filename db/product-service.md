# Product Service

## Назначение сервиса

`product-service` управляет каталогом лампочек, категориями, изображениями и остатками. Сервис отдает публичные данные витрине и защищенные административные операции для управления ассортиментом.

## Хранилище

- отдельная база данных PostgreSQL 16
- схема в пределах одного сервиса не разделяется с другими микросервисами
- денежные поля хранятся в копейках

## Таблицы

### `categories`

| Поле | Тип | Ограничения | Назначение |
| --- | --- | --- | --- |
| `id` | `bigserial` | PK | идентификатор категории |
| `name` | `varchar(120)` | not null, unique | отображаемое название |
| `slug` | `varchar(120)` | not null, unique | URL-идентификатор |
| `sort_order` | `integer` | not null default 0 | порядок вывода в каталоге |
| `is_active` | `boolean` | not null default true | признак доступности категории |
| `created_at` | `timestamptz` | not null | дата создания |
| `updated_at` | `timestamptz` | not null | дата обновления |

Индексы:

- `ux_categories_name`
- `ux_categories_slug`
- `ix_categories_is_active_sort`

### `products`

| Поле | Тип | Ограничения | Назначение |
| --- | --- | --- | --- |
| `id` | `bigserial` | PK | идентификатор товара |
| `sku` | `varchar(64)` | not null, unique | заводской артикул |
| `name` | `varchar(255)` | not null | название товара |
| `slug` | `varchar(255)` | not null, unique | URL-идентификатор |
| `description` | `text` | not null | маркетинговое описание |
| `category_id` | `bigint` | FK -> `categories.id`, not null | категория |
| `price_minor` | `integer` | not null, check > 0 | цена в копейках |
| `stock_qty` | `integer` | not null, check >= 0 | доступный остаток |
| `base_type` | `varchar(20)` | not null | тип цоколя, например `E27` |
| `wattage` | `smallint` | not null, check > 0 | мощность в ваттах |
| `color_temperature_k` | `smallint` | not null | цветовая температура |
| `luminous_flux_lm` | `smallint` | not null | световой поток |
| `is_active` | `boolean` | not null default true | видимость на витрине |
| `created_at` | `timestamptz` | not null | дата создания |
| `updated_at` | `timestamptz` | not null | дата обновления |

Индексы:

- `ux_products_sku`
- `ux_products_slug`
- `ix_products_category_id`
- `ix_products_is_active`
- `ix_products_price_minor`
- `ix_products_stock_qty`
- `ix_products_base_type`
- составной индекс `ix_products_catalog_filters(category_id, base_type, wattage, color_temperature_k, is_active)`

### `product_images`

| Поле | Тип | Ограничения | Назначение |
| --- | --- | --- | --- |
| `id` | `bigserial` | PK | идентификатор изображения |
| `product_id` | `bigint` | FK -> `products.id`, not null | товар |
| `image_url` | `text` | not null | путь к изображению |
| `alt_text` | `varchar(255)` | null | текст для accessibility |
| `sort_order` | `integer` | not null default 0 | порядок изображений |
| `created_at` | `timestamptz` | not null | дата создания |

Индексы:

- `ix_product_images_product_id_sort`

## Связи

- одна категория содержит много товаров
- один товар содержит много изображений
- удаление категории запрещено, если существуют связанные товары
- удаление товара должно каскадно удалять его изображения

## Бизнес-правила

- `stock_qty` не может быть отрицательным
- товар с `is_active = false` не отображается на витрине, но доступен в админке
- товар с `stock_qty = 0` отображается на витрине как недоступный
- `slug` должен генерироваться из `name`, но может редактироваться администратором
- фильтрация каталога опирается на поля `category_id`, `base_type`, `wattage`, `color_temperature_k`, `stock_qty`

## Соответствие прототипам

Поля карточки товара и каталога полностью покрываются таблицей `products`:

- название
- артикул
- описание
- цена
- категория
- тип цоколя
- мощность
- цветовая температура
- световой поток
- признак наличия
- изображения

## Основные API-операции

Публичные:

- `GET /categories`
- `GET /products`
- `GET /products/{id}`

Административные:

- `POST /products`
- `PATCH /products/{id}`
- `DELETE /products/{id}`
- `PATCH /products/{id}/stock`
- `POST /categories`
- `PATCH /categories/{id}`
- `DELETE /categories/{id}`

## Рекомендации по seed-данным

- загрузить 5 категорий
- загрузить 20 товаров согласно таблице из ТЗ
- для каждого товара хранить от 1 до 3 изображений
