# Author texts — лабораторная работа №3

Сервис карточек авторских текстов для расчёта TTR. Пользователь вводит количество
всех токенов и уникальных токенов; сервер вычисляет их отношение. Исходный текст,
автор произведения и год публикации не хранятся.

Ветка: `lab3-author_texts-api`. Основной контракт ЛР-3: `/api`.
Swagger: `http://127.0.0.1:8000/api/docs`, OpenAPI: `/api/openapi.json`.
Сохранённый SSR-интерфейс находится по `/author_texts` и не входит в десять API-методов.

## Десять HTTP-методов

Всего **3 GET, 5 POST, 1 PUT, 1 DELETE**. Во всех URL ниже уже указан префикс /api.
Card — постоянная схема карточки, описанная далее; Card[] — массив таких карточек.

| № | Метод | URL | Назначение и вход | Успешный ответ |
|---|---|---|---|---|
| 1 | GET | /api/author_texts | Список опубликованных текстов. Необязательный query min_text_length: integer ≥ 0 | 200, Card[] |
| 2 | GET | /api/author_texts/feed | Лента. Query author_text_id: integer ≥ 1, необязателен; next: boolean = false | 200, Card |
| 3 | GET | /api/author_texts/draft | Собственный черновик; ID с клиента не передаётся | 200, Card |
| 4 | POST | /api/author_texts | Создание: multipart work_title, author_texts_image, author_texts_video; все обязательны | 201, Card |
| 5 | PUT | /api/author_texts/{author_text_id}/publish | Публикация собственного черновика: JSON ниже; path author_text_id: integer | 200, Card |
| 6 | DELETE | /api/author_texts/{author_text_id} | Логическое удаление своего опубликованного текста; path author_text_id: integer | 200, пустое тело |
| 7 | POST | /api/author_texts/{author_text_id}/like | Лайк: JSON value: integer 0 или 1; path author_text_id: integer | 200, Card |
| 8 | POST | /api/author_texts_users/register | JSON username: string 1–80, password: string 8–128 | 201, author_texts_user_id: integer, username: string |
| 9 | POST | /api/author_texts_users/login | Аутентификация: заглушка ЛР-3, без входных данных | 200, пустое тело |
| 10 | POST | /api/author_texts_users/logout | Деавторизация: заглушка ЛР-3, без входных данных | 200, пустое тело |

Лента без ID возвращает первую опубликованную карточку. С ID — указанную карточку,
с ID и next=true — следующую; после последней происходит переход к первой.
Это один GET-метод с параметрами, не несколько методов. Отсутствующая или удалённая
карточка даёт 404. Пустой корпус возвращает [].

### Создание и публикация

POST принимает ровно три multipart-поля: название (1–200 символов), фото и видео.
Фото: JPEG/PNG/WebP до 10 МиБ. Видео: MP4/WebM до 50 МиБ.
Проверяются MIME, размер и сигнатура заголовка; длительность и полная декодируемость
не проверяются. Для демонстрации выбрать короткий ролик.
Файлы сохраняются в MinIO под именами `author_texts_<uuid>.<ext>`;
ключи сохраняются в БД. Ошибка загрузки/сохранения компенсируется удалением
только что загруженных файлов.

При «Далее» создаётся черновик: название и медиа заполнены, описание и два числа
могут быть NULL. Создатель и статус назначаются сервером. Второй черновик
одного пользователя запрещён частичным уникальным индексом.

PUT публикации принимает ровно следующие обязательные поля:

```json
{
  "work_title": "Проверка TTR",
  "short_description": "Проверка введённых показателей.",
  "text_length": 5,
  "unique_token_count": 3
}
```

Числа — именно целые JSON-числа, не строки и не boolean; диапазон 1–2147483647.
Уникальных токенов не может быть больше общего количества. TTR для примера равен 0.6.
Пустые название/описание запрещены. Неизвестные и системные поля отклоняются.
Публикация возможна только из собственного draft в published; возврата в draft нет.
DELETE переводит собственную published-карточку в deleted. Строка и файлы остаются.

### Постоянная схема Card

Все ключи присутствуют всегда, даже если значение NULL.

| Поле | Тип JSON | Значение |
|---|---|---|
| author_text_id | integer | ID карточки |
| work_title | string | Название произведения |
| short_description | string / null | Описание, до публикации может быть пустым |
| author_texts_image_url | string / null | Адрес изображения |
| author_texts_video_url | string / null | Адрес видео |
| text_length | integer / null | Введённое количество всех токенов |
| unique_token_count | integer / null | Введённое количество уникальных токенов |
| author_texts_ratio | number / null | unique_token_count / text_length |
| author_texts_like_count | integer | Общее количество лайков |
| is_owner | integer 0/1 | Создатель карточки совпадает с текущим пользователем |
| is_liked | integer 0/1 | Текущий пользователь уже поставил лайк |

Оба признака вычисляются для текущего пользователя, не хранятся в таблице текста.
В корпусе is_owner нужен для доступности удаления, в ленте is_liked — для сердца.
Признак в ответе не заменяет проверку владельца на сервере.
POST like с value=1 устанавливает лайк, value=0 снимает; повтор не создаёт дубликаты.

HTTP-код и статус draft/published/deleted в JSON не включаются. Ошибки имеют пустое тело:
404 — нет доступного объекта; 409 — второй черновик или занятое имя пользователя;
422 — некорректные данные; 503 — недоступность хранилища; 500 — непредвиденная ошибка.
Неверный HTTP-метод даёт 405.

## Таблицы PostgreSQL

### author_texts — карточки авторских текстов

| Поле | Тип | NULL | Ключ / назначение |
|---|---|---|---|
| author_text_id | integer | нет | PK, генерируется БД |
| work_title | varchar(200) | нет | Название, вводится до «Далее» |
| short_description | varchar(500) | да | Описание, обязательно при публикации |
| author_texts_status | varchar(9) | нет | draft / published / deleted, задаёт сервер |
| author_texts_image_url | varchar(500) | нет | Ключ фото в MinIO; для старых данных поддерживается URL |
| author_texts_video_url | varchar(500) | нет | Ключ видео в MinIO; для старых данных поддерживается URL |
| unique_token_count | integer | да | Уникальные токены, обязательно при публикации |
| text_length | integer | да | Все токены, обязательно при публикации |
| creator_id | integer | нет | FK → author_texts_users.author_texts_user_id, назначает сервер |

CHECK: числа неотрицательны и unique_token_count ≤ text_length.
API публикации дополнительно запрещает нули. Частичный UNIQUE по creator_id
при status=draft обеспечивает не более одного черновика на пользователя.
Миграция 20261018_05 удаляет author_name, publication_year, text_content.
Для прежних строк без медиа устанавливаются ссылки на стандартные SSR-файлы;
новые API-карточки требуют реальной загрузки обоих файлов.

### author_texts_users — пользователи

| Поле | Тип | NULL | Ключ / назначение |
|---|---|---|---|
| author_texts_user_id | integer | нет | PK, генерируется БД |
| username | varchar(80) | нет | UNIQUE, имя пользователя |
| password_hash | varchar(255) | нет | Хеш PBKDF2-SHA256, исходный пароль не хранится |

### author_texts_text_likes — лайки

| Поле | Тип | NULL | Ключ / назначение |
|---|---|---|---|
| author_texts_like_id | integer | нет | PK, генерируется БД |
| researcher_id | integer | нет | FK → author_texts_users.author_texts_user_id |
| author_text_id | integer | нет | FK → author_texts.author_text_id |

Пара (researcher_id, author_text_id) уникальна. Все FK используют RESTRICT,
каскадного удаления нет. Один пользователь создаёт 0..* карточек и ставит 0..* лайков;
каждый лайк относится ровно к одному пользователю и одной карточке.
