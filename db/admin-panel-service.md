# Admin Panel Service

## Назначение сервиса

`admin-panel-service` реализует аутентификацию администратора и BFF-слой для веб-админки. Сервис не владеет доменными данными каталога и заказов, а агрегирует и проксирует операции в `product-service` и `order-service`.

## Хранилище

- отдельная база данных PostgreSQL 16
- локально хранятся только учетные записи администраторов
- access token выдается по JWT и не хранится в базе

## Таблицы

### `admin_users`

| Поле | Тип | Ограничения | Назначение |
| --- | --- | --- | --- |
| `id` | `bigserial` | PK | идентификатор администратора |
| `login` | `varchar(64)` | not null, unique | логин |
| `password_hash` | `varchar(255)` | not null | хэш пароля |
| `full_name` | `varchar(255)` | not null | отображаемое имя |
| `role` | `varchar(32)` | not null default `admin` | роль пользователя |
| `is_active` | `boolean` | not null default true | активность записи |
| `last_login_at` | `timestamptz` | null | дата последнего входа |
| `created_at` | `timestamptz` | not null | дата создания |
| `updated_at` | `timestamptz` | not null | дата обновления |

Индексы:

- `ux_admin_users_login`
- `ix_admin_users_is_active`

## BFF-ответственность

Сервис предоставляет единый backend для административного SPA-клиента:

- валидирует JWT для всех защищенных endpoint
- получает данные каталога из `product-service`
- получает данные заказов из `order-service`
- нормализует формат ответов для фронтенда админки
- при необходимости объединяет данные нескольких сервисов в один DTO

## Данные, которые сервис не хранит

- товары
- категории
- остатки
- корзины
- заказы
- история статусов заказов

## Основные endpoint

### Auth

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

### BFF: каталог

- `GET /catalog/products`
- `GET /catalog/products/{id}`
- `POST /catalog/products`
- `PATCH /catalog/products/{id}`
- `DELETE /catalog/products/{id}`
- `PATCH /catalog/products/{id}/stock`
- `GET /catalog/categories`
- `POST /catalog/categories`
- `PATCH /catalog/categories/{id}`
- `DELETE /catalog/categories/{id}`

### BFF: заказы

- `GET /orders`
- `GET /orders/{id}`
- `PATCH /orders/{id}/status`
- `GET /dashboard/summary`

## Бизнес-правила

- войти в админку может только активный пользователь с ролью `admin`
- все BFF endpoint, кроме `POST /auth/login`, защищены JWT
- `POST /auth/logout` завершает клиентскую сессию логически: фронтенд удаляет токен, сервер возвращает `204 No Content`
- BFF должен сохранять понятные коды ошибок доменных сервисов и добавлять трассировку для фронтенда
- формат ошибок для фронтенда единый: `code`, `message`, `details`, `traceId`

## Соответствие прототипам

Схема и API покрывают:

- страницу входа
- список товаров
- форму товара
- экран категорий
- список заказов
- карточку заказа
- панель быстрых метрик на dashboard

## Пример seed-данных

- `login`: `admin`
- `password_hash`: хэш пароля `Admin123!`
- `full_name`: `Администратор завода`
- `role`: `admin`
