# Order Service

## Назначение сервиса

`order-service` управляет корзиной, оформлением заказов, позициями заказа и историей изменений статусов. Сервис хранит слепок данных о товарах на момент заказа, чтобы заказ не зависел от последующих изменений каталога.

## Хранилище

- отдельная база данных PostgreSQL 16
- корзина хранится по анонимному `session_id`
- заказ после оформления не зависит от актуального состояния каталога

## Таблицы

### `carts`

| Поле | Тип | Ограничения | Назначение |
| --- | --- | --- | --- |
| `id` | `bigserial` | PK | идентификатор корзины |
| `session_id` | `uuid` | not null, unique | идентификатор гостевой сессии |
| `created_at` | `timestamptz` | not null | дата создания |
| `updated_at` | `timestamptz` | not null | дата последнего изменения |

Индексы:

- `ux_carts_session_id`

### `cart_items`

| Поле | Тип | Ограничения | Назначение |
| --- | --- | --- | --- |
| `id` | `bigserial` | PK | идентификатор позиции |
| `cart_id` | `bigint` | FK -> `carts.id`, not null | корзина |
| `product_id` | `bigint` | not null | идентификатор товара из `product-service` |
| `product_name` | `varchar(255)` | not null | снимок названия для корзины |
| `sku` | `varchar(64)` | not null | снимок артикула |
| `unit_price_minor` | `integer` | not null | цена единицы в копейках |
| `qty` | `integer` | not null, check > 0 | количество |
| `line_total_minor` | `integer` | not null | сумма по позиции |
| `created_at` | `timestamptz` | not null | дата создания |
| `updated_at` | `timestamptz` | not null | дата обновления |

Индексы:

- `ux_cart_items_cart_product(cart_id, product_id)`
- `ix_cart_items_cart_id`

### `orders`

| Поле | Тип | Ограничения | Назначение |
| --- | --- | --- | --- |
| `id` | `bigserial` | PK | внутренний идентификатор заказа |
| `order_number` | `varchar(32)` | not null, unique | внешний номер заказа |
| `session_id` | `uuid` | not null | сессия покупателя |
| `customer_name` | `varchar(255)` | not null | имя покупателя |
| `phone` | `varchar(32)` | not null | телефон |
| `email` | `varchar(255)` | not null | email |
| `delivery_type` | `varchar(20)` | not null | `pickup` или `courier` |
| `address` | `text` | null | адрес доставки |
| `comment` | `text` | null | комментарий покупателя |
| `status` | `varchar(20)` | not null | текущий статус |
| `items_count` | `integer` | not null | количество строк заказа |
| `total_minor` | `integer` | not null | общая сумма |
| `created_at` | `timestamptz` | not null | дата оформления |
| `updated_at` | `timestamptz` | not null | дата обновления |

Индексы:

- `ux_orders_order_number`
- `ix_orders_status_created_at`
- `ix_orders_phone`
- `ix_orders_email`
- `ix_orders_session_id`

### `order_items`

| Поле | Тип | Ограничения | Назначение |
| --- | --- | --- | --- |
| `id` | `bigserial` | PK | идентификатор позиции заказа |
| `order_id` | `bigint` | FK -> `orders.id`, not null | заказ |
| `product_id` | `bigint` | not null | идентификатор товара из каталога |
| `sku` | `varchar(64)` | not null | снимок артикула |
| `product_name` | `varchar(255)` | not null | снимок названия |
| `base_type` | `varchar(20)` | not null | снимок цоколя |
| `wattage` | `smallint` | not null | снимок мощности |
| `color_temperature_k` | `smallint` | not null | снимок температуры |
| `unit_price_minor` | `integer` | not null | цена единицы |
| `qty` | `integer` | not null, check > 0 | количество |
| `line_total_minor` | `integer` | not null | сумма позиции |
| `created_at` | `timestamptz` | not null | дата создания |

Индексы:

- `ix_order_items_order_id`

### `order_status_history`

| Поле | Тип | Ограничения | Назначение |
| --- | --- | --- | --- |
| `id` | `bigserial` | PK | идентификатор записи |
| `order_id` | `bigint` | FK -> `orders.id`, not null | заказ |
| `from_status` | `varchar(20)` | null | предыдущий статус |
| `to_status` | `varchar(20)` | not null | новый статус |
| `changed_by` | `varchar(64)` | not null | идентификатор администратора или system |
| `comment` | `text` | null | примечание к смене статуса |
| `created_at` | `timestamptz` | not null | дата изменения |

Индексы:

- `ix_order_status_history_order_id_created_at`

## Разрешенные статусы

- `new`
- `confirmed`
- `packing`
- `shipped`
- `completed`
- `cancelled`

## Разрешенные переходы

- `new -> confirmed`
- `new -> cancelled`
- `confirmed -> packing`
- `confirmed -> cancelled`
- `packing -> shipped`
- `packing -> cancelled`
- `shipped -> completed`

## Бизнес-правила

- корзина не может содержать дубли по одному и тому же `product_id`
- позиция корзины должна пересчитывать `line_total_minor` после каждого изменения `qty`
- при создании заказа сервис повторно проверяет остаток в `product-service`
- после успешного заказа данные из корзины копируются в `orders` и `order_items`
- после успешного оформления корзина очищается
- `address` обязательно только для `delivery_type = courier`
- изменение статуса заказа возможно только по допустимым переходам

## Соответствие прототипам

Схема покрывает:

- корзину и позиции корзины
- экран checkout с контактными данными и способом получения
- страницу подтверждения заказа
- таблицу заказов в админке
- карточку заказа и историю статусов

## Основные API-операции

- `GET /cart/{sessionId}`
- `POST /cart/{sessionId}/items`
- `PATCH /cart/{sessionId}/items/{itemId}`
- `DELETE /cart/{sessionId}/items/{itemId}`
- `DELETE /cart/{sessionId}`
- `POST /orders`
- `GET /orders/{orderId}`
- `GET /admin/orders`
- `GET /admin/orders/{orderId}`
- `PATCH /admin/orders/{orderId}/status`
