FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 app

COPY benchmark/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY benchmark/main.py .

RUN chown -R app:app /app

USER app

EXPOSE 8001

CMD ["python", "main.py"]