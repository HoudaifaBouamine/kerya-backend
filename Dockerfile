FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_CREATE=false

# system deps
RUN apt-get update && apt-get install -y build-essential libpq-dev gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install pip deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy project
COPY . /app

# entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PATH="/root/.local/bin:${PATH}"

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "kerya.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
