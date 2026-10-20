# Author texts — лабораторная работа №4

Веб-сервис карточек авторских текстов для темы «История и культура», вариант 11.
Пользователь вводит количество всех и уникальных токенов; сервер рассчитывает
TTR как их отношение. Исходный текст, автор произведения и год публикации не хранятся.

Стек: Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, MinIO, Redis.
Ветка: `lab4-author_texts-auth`.

## HTTP-методы

Базовый адрес: `http://127.0.0.1:8000/api`.
Swagger: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs).
Спецификация OpenAPI: `/api/openapi.json`.
Всего 10 методов: 3 GET, 5 POST, 1 PUT, 1 DELETE.

| Метод | URL | Входные данные | Успешный ответ |
|---|---|---|---|
| GET | `/api/author_texts` | Необязательный query `min_text_length`: integer ≥ 0 | 200, Card[] опубликованных текстов |
| GET | `/api/author_texts/feed` | Необязательные query `author_text_id`: integer ≥ 1 и `next`: boolean = false | 200, Card |
| GET | `/api/author_texts/draft` | Сессионная cookie; ID не передаётся | 200, Card собственного черновика |
| POST | `/api/author_texts` | Cookie; multipart `work_title`, `author_texts_image`, `author_texts_video`; все обязательны | 201, Card нового черновика |
| PUT | `/api/author_texts/{author_text_id}/publish` | Cookie; ID в URL; JSON публикации | 200, Card опубликованного текста |
| DELETE | `/api/author_texts/{author_text_id}` | Cookie; ID собственной опубликованной карточки | 200, пустое тело |
| POST | `/api/author_texts/{author_text_id}/like` | Cookie; ID в URL; JSON `value`: integer 0 или 1 | 200, Card с обновлёнными лайками |
| POST | `/api/author_texts_users/register` | JSON `username`: string 1–80, `password`: string 8–128 | 201, `author_texts_user_id`, `username` |
| POST | `/api/author_texts_users/login` | JSON `username`, `password` | 200, `author_texts_user_id`, `username`; заголовок Set-Cookie |
| POST | `/api/author_texts_users/logout` | Сессионная cookie; тело не требуется | 200, пустое тело |

Лента без ID возвращает первую опубликованную карточку, с ID — выбранную,
с ID и `next=true` — следующую с переходом к первой после последней.
Корпус и лента доступны гостю. Удалённые карточки не выдаются.

### Создание и публикация

Создание требует названия длиной 1–200 символов и двух файлов: изображения
JPEG/PNG/WebP до 10 МиБ и видео MP4/WebM до 50 МиБ. Файлы сохраняются в MinIO
под уникальными латинскими именами, ключи — в PostgreSQL.

Тело запроса публикации:

```json
{
  "work_title": "Проверка TTR",
  "short_description": "Проверка введённых показателей.",
  "text_length": 5,
  "unique_token_count": 3
}
```

Все четыре поля обязательны. Описание — до 500 символов. Количества токенов —
положительные целые числа до 2147483647, уникальных не больше общего количества.
Для примера TTR равен 0.6. Неизвестные и системные поля не принимаются.

Жизненный цикл: `draft → published → deleted`. Возврат в черновик запрещён.
У пользователя не более одного черновика. Создатель, статус и даты назначаются
сервером. Публиковать и удалять можно только собственные карточки.
Логическое удаление сохраняет строку в БД и файлы в MinIO.
Лайк с `value=1` устанавливается, с `value=0` снимается; повтор не создаёт дубликаты.

### Схема Card

Все ключи присутствуют в каждом ответе, в том числе при значении `null`.

| Поле | Тип JSON | Назначение |
|---|---|---|
| `author_text_id` | integer | ID карточки |
| `work_title` | string | Название произведения |
| `short_description` | string / null | Краткое описание |
| `author_texts_image_url` | string / null | Адрес изображения |
| `author_texts_video_url` | string / null | Адрес видео |
| `unique_token_count` | integer / null | Количество уникальных токенов |
| `text_length` | integer / null | Количество всех токенов |
| `author_texts_ratio` | number / null | TTR: уникальные токены / все токены |
| `author_texts_like_count` | integer | Количество лайков |
| `is_owner` | integer 0/1 | Карточка создана текущим пользователем |
| `is_liked` | integer 0/1 | Текущий пользователь поставил лайк |

Два персональных признака и количество лайков вычисляются сервером.
HTTP-код и статус жизненного цикла в JSON не дублируются.
Ошибки возвращаются с пустым телом: 401 — требуется вход или неверный пароль;
403 — недопустимый Origin; 404 — объект недоступен; 409 — занятое имя или второй
черновик; 422 — неверные данные; 503 — недоступность хранилища.

## Аутентификация и авторизация

Пароли хранятся как хеши PBKDF2-SHA256. Регистрация не выполняет автоматический вход.
При входе сервер создаёт сессию Redis со случайным идентификатором и сроком 3600 секунд.
Ключ `author_texts:session:<идентификатор>` содержит ID пользователя.

Cookie `author_texts_session`: HttpOnly, SameSite=Lax, Path=/api.
В локальном HTTP Secure отключён; для HTTPS используется
`AUTHOR_TEXTS_COOKIE_SECURE=true`. Браузер сохраняет cookie после входа автоматически.

Создание, получение черновика, публикация, удаление и лайки требуют действующей
сессии. Текущий пользователь определяется по Redis, а не константой и не полями
запроса. При выходе сессия отзывается и cookie удаляется.

## Таблицы PostgreSQL

### author_texts

| Поле | Тип | NULL | Назначение |
|---|---|---|---|
| `author_text_id` | integer | нет | PK, генерируется БД |
| `work_title` | varchar(200) | нет | Название |
| `short_description` | varchar(500) | да | Описание, обязательно при публикации |
| `author_texts_status` | varchar(9) | нет | draft / published / deleted |
| `author_texts_image_url` | varchar(500) | нет | Ключ изображения в MinIO |
| `author_texts_video_url` | varchar(500) | нет | Ключ видео в MinIO |
| `unique_token_count` | integer | да | Уникальные токены, обязательно при публикации |
| `text_length` | integer | да | Все токены, обязательно при публикации |
| `creator_id` | integer | нет | FK → author_texts_users.author_texts_user_id |
| `created_at` | timestamp with time zone | нет | Дата создания, DEFAULT now() |
| `published_at` | timestamp with time zone | да | Дата формирования при публикации |

CHECK: количества неотрицательны, `unique_token_count ≤ text_length`.
Частичный UNIQUE по `creator_id` при `author_texts_status='draft'` запрещает второй черновик.
Для старых строк допускаются полные адреса медиа и неизвестная дата публикации.

### author_texts_users

| Поле | Тип | NULL | Назначение |
|---|---|---|---|
| `author_texts_user_id` | integer | нет | PK, генерируется БД |
| `username` | varchar(80) | нет | UNIQUE, имя пользователя |
| `password_hash` | varchar(255) | нет | Хеш пароля |

### author_texts_text_likes

| Поле | Тип | NULL | Назначение |
|---|---|---|---|
| `author_texts_like_id` | integer | нет | PK, генерируется БД |
| `researcher_id` | integer | нет | FK → author_texts_users.author_texts_user_id |
| `author_text_id` | integer | нет | FK → author_texts.author_text_id |

Пара `(researcher_id, author_text_id)` уникальна. Все внешние ключи используют
RESTRICT; каскадного удаления нет. Один пользователь создаёт 0..* карточек
и ставит 0..* лайков. Каждый лайк связан с одним пользователем и одной карточкой.

## Запуск

Требуется Docker Compose и соседний репозиторий
[lexical-diversity-frontend](https://github.com/Teddy-Ro/lexical-diversity-frontend/tree/lab3-author_texts-api)
ветки `lab3-author_texts-api` в каталоге `../lexical-diversity-frontend`.
Он содержит SSR-шаблоны и статические файлы приложения.

```powershell
git clone --branch lab3-author_texts-api https://github.com/Teddy-Ro/lexical-diversity-frontend.git ../lexical-diversity-frontend
docker compose --profile full up -d --build
```

Клонирование требуется только при отсутствии каталога фронтенда.
При запуске контейнера автоматически применяются миграции и добавляются исходные данные.
SSR-просмотр корпуса и ленты: `http://127.0.0.1:8000/author_texts`.
В ЛР-4 операции создания и изменения выполняются через REST API.
