# TTR Backend — лабораторная работа №2

FastAPI-приложение для расчёта лексического разнообразия авторских текстов.
Данные хранятся в PostgreSQL, запросы выполняются асинхронно через SQLAlchemy
и `asyncpg`, структура БД управляется Alembic.

## Быстрый запуск в Docker

Выберите один способ запуска backend: целиком в Docker или локально через
`python author_texts_main.py`. Одновременно использовать оба способа не нужно, поскольку
оба занимают порт `8000`.

```powershell
docker compose --profile full up -d --build
```

- приложение: <http://127.0.0.1:8000/author_texts>;
- Adminer: <http://127.0.0.1:8080>;
- MinIO: <http://127.0.0.1:9001>.

PostgreSQL внутри Docker работает на `5432`, а на Windows опубликован через
`55432`, чтобы не конфликтовать с локальной установкой PostgreSQL.

Данные для входа в Adminer:

```text
Система: PostgreSQL
Сервер: ttr-postgres
Пользователь: author_texts_user
Пароль: ttr_password
База данных: author_texts_database
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
python -m data.author_texts_seed
python author_texts_main.py
```

При локальном запуске приложение доступно на <http://127.0.0.1:8000>.

## Модель данных

- `author_texts_users` — пользователи и создатели текстов;
- `author_texts` — тексты со статусами `draft`, `published`, `deleted`;
- `author_texts_text_likes` — связь многие-ко-многим пользователей и текстов.

На одного пользователя допускается только один черновик. Каскадное удаление
не используется. Количество токенов, уникальных токенов и TTR вычисляются из
введённого текста без учёта регистра. Новые фото и видео в ЛР-2 не сохраняются.
В `author_texts_users.password_hash` хранится хеш пароля, не исходный пароль.
У новых демонстрационных пользователей пароль `author_texts_demo`; у ранее
созданных пользователей при миграции установлен случайный неизвестный пароль.
Авторизация в ЛР-2 не реализуется.

## Добавление и стандартные медиа

До «Далее» доступны только название и две отдельные кнопки выбора видео и фото.
Файлы можно выбрать на устройстве, но они намеренно не отправляются и не сохраняются.
«Далее» создаёт черновик; обновление страницы само по себе ничего не создаёт.
После «Далее» пользователь заполняет автора, необязательный год, описание и текст.
Публикация рассчитывает `text_length` и `unique_token_count` из текста автоматически.
Остальные поля до публикации допускают `NULL`, потому что черновик ещё не заполнен.

Резервные фото и видео лежат в `public/media` frontend и отдаются SSR-сервером
по `/author_texts-assets/media/author_texts_default.jpg` и `.webm`.
Они подставляются, если соответствующее поле медиа пустое. Собственные медиа
демонстрационных карточек по-прежнему находятся в MinIO.
Имя bucket — `author-texts-media`: S3/MinIO не допускает подчёркивания в именах bucket.
JavaScript в шаблонах нет: фильтр отправляется обычной GET-формой.

## Где считаются лайки

В `api/author_texts_handlers.py`, функция `prepare_author_texts_text`:
`len(author_texts_text.likes)`. Связанные строки загружаются через
`selectinload(AuthorText.likes)`, число передаётся в шаблон как
`author_texts_like_count`. Сердце пока только отображает это число.

## Шесть HTTP-методов ЛР-2

- `GET /author_texts` — корпус и фильтрация по длине;
- `GET /author_texts/add` — форма нового текста или существующего черновика;
- `GET /author_texts/{author_text_id}` — опубликованный текст в ленте;
- `POST /author_texts/drafts` — создание черновика по кнопке «Далее» через ORM;
- `POST /author_texts/{author_text_id}/publish` — публикация через ORM;
- `POST /author_texts/{author_text_id}/delete` — логическое удаление сырым SQL `UPDATE`.

## Проверка

```powershell
python -m pip install -r requirements-dev.txt
$env:AUTHOR_TEXTS_RUN_DB_TESTS = '1'
python -m unittest discover -s tests -p "author_texts_test_*.py"
python -m alembic check
```

Интеграционный тест откатывает свои строки после проверки. Он проверяет
«Далее → публикация → фильтр → лайки → следующий → удаление → 404».
БД называется `author_texts_database`, роль подключения — `author_texts_user`.
Пароль при переименовании не изменялся. Исторические миграции и инфраструктурные
контейнеры/тома сохраняют старый префикс для совместимости с существующими данными.
Таблицы приложения и HTTP-адреса используют `author_texts`.
Перед миграцией требуется резервная копия; удалённые служебные
даты `created_at`/`published_at` можно восстановить только из неё.

ER-диаграмма и перечень скриншотов находятся в каталоге `docs`.
