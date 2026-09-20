# TTR Backend

Лабораторная работа №1 на FastAPI и Jinja2.

- Тема: «Расчёт лексического разнообразия текстов автора TTR».
- Карточка: `ttr_text` — текст автора.
- Предметные поля: `unique_token_count` и `text_length`.
- Фильтрация: минимальная длина текста.
- Префикс предметной области: `ttr`.
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

Для запуска без Docker медиа можно раздавать через FastAPI.

Windows PowerShell:

```powershell
$env:TTR_MINIO_PUBLIC_URL = "http://127.0.0.1:8000/ttr-media"
python main.py
```

macOS/Linux:

```bash
TTR_MINIO_PUBLIC_URL=http://127.0.0.1:8000/ttr-media python main.py
```

Приложение: <http://127.0.0.1:8000/>.

## Три GET-маршрута

- `GET /ttr-texts?min_text_length=100000` — плитка и фильтр-слайдер.
- `GET /ttr-texts/add` — форма добавления без сохранения.
- `GET /ttr-texts/{ttr_text_id}` — лента с выбранного текста.

В первой лабораторной базы данных нет: данные хранятся в коллекции
`TTR_TEXTS`. Статус используется только для серверного выбора опубликованных
карточек и черновика, но не отображается в интерфейсе.
