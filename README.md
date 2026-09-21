# TTR Backend — лабораторная работа №2

FastAPI-приложение для расчёта лексического разнообразия авторских текстов.
Данные хранятся в PostgreSQL, запросы выполняются асинхронно через SQLAlchemy
и `asyncpg`, структура БД управляется Alembic.

## Быстрый запуск в Docker

Выберите один способ запуска backend: целиком в Docker или локально через
`python main.py`. Одновременно использовать оба способа не нужно, поскольку
оба занимают порт `8000`.

```powershell
docker compose --profile full up -d --build
```

- приложение: <http://127.0.0.1:8000/ttr-texts>;
- Adminer: <http://127.0.0.1:8080>;
- MinIO: <http://127.0.0.1:9001>.

PostgreSQL внутри Docker работает на `5432`, а на Windows опубликован через
`55432`, чтобы не конфликтовать с локальной установкой PostgreSQL.

Данные для входа в Adminer:

```text
Система: PostgreSQL
Сервер: ttr-postgres
Пользователь: ttr_user
Пароль: ttr_password
База данных: ttr_database
```

При запуске backend-контейнер сам применяет миграции и один раз добавляет
демонстрационные данные.

## Локальный запуск backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d ttr-postgres ttr-adminer ttr-minio ttr-minio-seed
python -m alembic upgrade head
python -m data.ttr_seed
python main.py
```

При локальном запуске приложение доступно на <http://127.0.0.1:8000>.

## Модель данных

- `ttr_users` — пользователи и создатели текстов;
- `ttr_texts` — тексты со статусами `draft`, `published`, `deleted`;
- `ttr_text_likes` — связь многие-ко-многим пользователей и текстов.

На одного пользователя допускается только один черновик. Каскадное удаление
не используется. Количество токенов, уникальных токенов и TTR вычисляются из
введённого текста без учёта регистра. Новые фото и видео в ЛР-2 не сохраняются.

## Шесть HTTP-методов ЛР-2

- `GET /ttr-texts` — корпус и фильтрация по длине;
- `GET /ttr-texts/add` — создание или продолжение черновика;
- `GET /ttr-texts/{ttr_text_id}` — опубликованный текст в ленте;
- `POST /ttr-texts/drafts` — добавление и публикация нового текста через ORM;
- `POST /ttr-texts/{ttr_text_id}/publish` — публикация через ORM;
- `POST /ttr-texts/{ttr_text_id}/delete` — логическое удаление сырым SQL `UPDATE`.

## Проверка

```powershell
python -m unittest discover -s tests -p "ttr_test_*.py"
python -m alembic check
```

ER-диаграмма и перечень скриншотов находятся в каталоге `docs`.
