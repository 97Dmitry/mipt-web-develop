# Артефакты по ТЗ

## Основные материалы

- [Техническое задание](./technical-spec.md)
- [Figma-прототипы](https://www.figma.com/design/ylKRkyzlLtbspdLxWrHx6n)

## Документация по БД

- [Product Service](./db/product-service.md)
- [Order Service](./db/order-service.md)
- [Admin Panel Service](./db/admin-panel-service.md)

## Postman

- `postman/product-service.postman_collection.json`
- `postman/order-service.postman_collection.json`
- `postman/admin-panel-service.postman_collection.json`

## Микросервисы

`docker-compose.yml` поднимает три прикладных микросервиса и три изолированные БД:

- `product-service` (`localhost:3001`) управляет товарами, категориями, остатками и публичной витриной `/public/*`.
- `order-service` (`localhost:3002`) управляет гостевой корзиной, оформлением заказа и admin endpoint заказов `/admin/orders*`.
- `admin-panel-service` (`localhost:3003`) выдает JWT для менеджера и проксирует admin-операции через BFF endpoints `/catalog/*`, `/orders*`, `/dashboard/summary`.

## JWT и внутренние вызовы

- `POST /auth/login` (`admin-panel-service`) выдает access token.
- `GET /auth/me`, `POST /auth/logout` требуют Bearer token.
- Browser-facing admin frontend должен ходить только в `admin-panel-service`.
- `product-service` и `order-service` валидируют JWT для своих прямых admin endpoint.
- `product-service /internal/*` закрыт `X-Internal-Token`; его вызывает только `order-service`.

Переменные окружения (см. `docker-compose.yml`):

- `ADMIN_LOGIN`
- `ADMIN_PASSWORD`
- `ADMIN_FULL_NAME`
- `JWT_SECRET`
- `JWT_ALG`
- `JWT_EXPIRES_MIN`
- `INTERNAL_API_TOKEN`

## Авто-заполнение каталога в контейнере

`product-service` запускает `python seed.py` перед `uvicorn`.

- скрипт сначала создаёт таблицы;
- затем проверяет, пустая ли БД (`categories=0` и `products=0`);
- если пустая — добавляет 5 категорий и 20 товаров с изображениями;
- если не пустая — пропускает заполнение.

Отключить авто-seed можно через `SEED_CATALOG_ON_START=false`.

## Исполнитель
Цыбизов Дмитрий Анатольевич
