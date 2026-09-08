# Lexical Diversity Backend

Лабораторная работа №1 на FastAPI и Jinja2.

- Тема: «Расчёт лексического разнообразия текстов автора TTR».
- Карточка: `author_text` — текст автора.
- Поля: `token_count` и `unique_type_count`.
- Филолог создаёт исследование, куратор корпуса модерирует карточки.
- Дизайн-референс: [CapsToLowercase](https://www.capstolowercase.com/lexical-diversity-calculator).

## Запуск

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
docker compose up -d
python main.py
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
docker compose up -d
python main.py
```

Для запуска без Docker медиа можно раздавать непосредственно через FastAPI.

Windows PowerShell:

```powershell
$env:MINIO_PUBLIC_URL = "http://127.0.0.1:8000/media"
python main.py
```

macOS/Linux:

```bash
MINIO_PUBLIC_URL=http://127.0.0.1:8000/media python main.py
```

Приложение: <http://127.0.0.1:8000/> (перенаправляет на `/author-texts`).

## Три GET-маршрута

- `GET /author-texts?min_unique_words=9000` — плитка и фильтр.
- `GET /author-texts/draft` — черновик без сохранения.
- `GET /author-texts/{author_text_id}` — лента с выбранного текста.

В первой лабораторной БД нет: данные хранятся в одной Python-коллекции.
