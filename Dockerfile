FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . /app/backend/

CMD ["/bin/sh", "-c", "python -m alembic upgrade head && python -m data.ttr_seed && uvicorn main:app --host 0.0.0.0 --port 8000"]
