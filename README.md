# Kerya — README

> **Overview**
>
> Kerya App is a multi-functional digital platform that connects hosts (property/event owners) and clients (renters/attendees) across Algeria and French/Arabic-speaking regions. Think Airbnb + local events + a reverse marketplace. Key capabilities:
>
> * Short-term rentals (houses, villas, chalets)
> * Hotel bookings
> * Local event discovery
> * Reverse marketplace: "Post a Budget"
> * Secure messaging and booking system
>
> The app solves friction in informal rental markets: trust, scams, low-quality listings, and lack of localized platforms.
>
> **Vision**: "Your journey, your rules — Kerya makes it possible."

---

## Quick facts (TL;DR)

* Dev: Django app runs locally (not in Docker) to maximize developer experience. BaaS (Postgres, Redis, MinIO, pgAdmin) run in Docker during development via `docker-compose.override.yml`.
* Prod: Django (`web`) and `celery` are built and run inside Docker when you explicitly merge `docker-compose.prod.yml` with the base compose file.
* Compose files:

  * `docker-compose.yml` — base (infrastructure services)
  * `docker-compose.override.yml` — development overrides (auto-merged by `docker compose up`)
  * `docker-compose.prod.yml` — production services (explicit merge via `-f`)

---

## Repo layout (important bits)

```text
./
├── docker-compose.yml
├── docker-compose.override.yml
├── docker-compose.prod.yml
├── Dockerfile
├── Dockerfile.celery
├── entrypoint.sh
├── kerya/              # Django project
│   ├── app/            # main app package (controllers, models, services)
│   ├── celery.py
│   └── settings/       # base.py, dev.py, prod.py
├── manage.py
├── nginx/nginx.conf
├── requirements.txt
└── static/
```

---

# Development guide

This assumes you have Docker (or Docker Desktop) and Python 3.11 installed locally.

### 1) Start infrastructure services (dev)

Development uses the `base` compose + `override` (override is automatically merged by `docker compose up`):

```bash
# from project root
docker compose up -d
# this runs Postgres, Redis, MinIO, pgAdmin bound to development ports
```

Ports (dev):

* Postgres: `localhost:9905` (mapped to 5432)
* Redis: `localhost:9903` (mapped to 6379)
* MinIO API: `localhost:9901` (mapped to 9000)
* MinIO Console: `localhost:9902` (mapped to 9001)
* pgAdmin: `localhost:9904`

All the ports are mapped on the dev and only nginx is mapped on the prod

### 2) Prepare local Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # if you provide an example; otherwise create .env manually
```

Example DB\_URL when using mapped port: `postgres://kerya:kerya@localhost:9905/kerya_db`

### 3) Run migrations and create superuser

```bash
python manage.py migrate
python manage.py collectstatic --noinput    # optional in dev
python manage.py createsuperuser
```

### 4) Start local Django server

```bash
python manage.py runserver
```

Open `http://localhost:8000`.

### 5) Useful dev commands

```bash
# stop infra
docker compose down

# show logs
docker compose logs -f
```

---

# Production deployment guide

Production runs Django `web` and `celery` in Docker images using `docker-compose.prod.yml` merged explicitly with base compose.

### 1) Prepare production environment

* Place a production `.env` on the host (never check it into git). Use strong secrets.
* Ensure a reverse proxy (Nginx) is configured (we provide `nginx/nginx.conf` as a starting point).
* Configure SSL (Let’s Encrypt, certbot, or a cloud load balancer). `nginx` container exposes 80/443.

### 2) Example commands (build + run)

```bash
# from project root: build and run prod stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

```

Notes:

* The `web` service uses `gunicorn` via the `command` defined in `docker-compose.prod.yml`.
* `nginx` maps the `static_volume` into the container as read-only so static assets are served by Nginx.

### 3) Celery in production

`celery` service is built using `Dockerfile.celery`.

Restarting Celery:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart celery
```

### 4) Logging & monitoring (practical)

* Stream logs: `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web`.
* Keep `DEBUG=False` and configure `ALLOWED_HOSTS` strictly.
* todo: Add Sentry for bug monitoring.

### 5) Backups & maintenance

* Postgres: schedule `pg_dump` to a safe storage or use managed DB backups.
* MinIO: enable versioning or snapshot underlying volume.
* Rotate secrets regularly and use an environment-specific `.env` or secret manager.

---

# Settings & environment differences

* `kerya/settings/dev.py`: local developer configuration (DEBUG=True, local databases, useful logging).
* `kerya/settings/prod.py`: production configuration (DEBUG=False, secure settings, S3/MinIO endpoints using internal docker hostnames: `minio:9000`).

Make sure your `.env` and `settings` agree on whether services are addressed by Docker hostnames (e.g. `db`, `redis`, `minio`) vs. `localhost:9905` mapped ports.

---

# Troubleshooting

* **DB connection refused**: ensure Postgres container is healthy (`docker compose ps`) and your `.env` contains correct host/port. In dev, use mapped port `9905` or use `db:5432` if running Django inside Docker network.
* **Static files 404 in prod**: ensure `collectstatic` ran and `static_volume` is mounted into `nginx` container.
* **Celery tasks not running**: check Redis connectivity and Celery logs; start worker manually to reproduce task failures.
* **MinIO permission errors**: double-check `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` and bucket policies.

---

# Common commands cheat-sheet

```bash
# dev infra
docker compose up -d

# stop infra
docker compose down

# build prod and run (build only web app and celery service)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# run one-off commands in prod web image
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm web python manage.py migrate
```
