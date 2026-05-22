# Артефакты по ТЗ

## Основные материалы

- [Техническое задание](./technical-spec.md)
- [Figma-прототипы](https://www.figma.com/design/ylKRkyzlLtbspdLxWrHx6n)

## Документация по БД

- [Product Service](./db/product-service.md)
- [Order Service](./db/order-service.md)
- [Admin Panel Service](./db/admin-panel-service.md)

## Postman

- `docs/postman/product-service.postman_collection.json`
- `docs/postman/order-service.postman_collection.json`
- `docs/postman/admin-panel-service.postman_collection.json`

## JWT для админки (ДЗ5)

Текущая реализация ДЗ5 не поднимает отдельный `admin-panel-service`: JWT и admin endpoint размещены в `order-service` + `product-service`.

- `POST /auth/login` (`order-service`) выдает access token.
- `GET /auth/me`, `POST /auth/logout` требуют Bearer token.
- Все admin-операции в `product-service` и `order-service` требуют Bearer token.
- Публичная витрина в `product-service` вынесена в `/public/*`.

Переменные окружения (см. `docker-compose.yml`):

- `ADMIN_LOGIN`
- `ADMIN_PASSWORD`
- `ADMIN_FULL_NAME`
- `JWT_SECRET`
- `JWT_ALG`
- `JWT_EXPIRES_MIN`

## Авто-заполнение каталога в контейнере

`product-service` запускает `python seed.py` перед `uvicorn`.

- скрипт сначала создаёт таблицы;
- затем проверяет, пустая ли БД (`categories=0` и `products=0`);
- если пустая — добавляет 5 категорий и 20 товаров с изображениями;
- если не пустая — пропускает заполнение.

Отключить авто-seed можно через `SEED_CATALOG_ON_START=false`.

## Исполнитель
Цыбизов Дмитрий Анатольевич
