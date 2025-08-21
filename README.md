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

## Dev & Prod Quick Overview

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
cp .env.example .env
```

### 3) Run migrations and create superuser

```bash
python manage.py migrate
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

Production runs all the previous BaaS (without port binging to localhost) in addition to Django `web`, `celery` and `nginx` in Docker images using `docker-compose.prod.yml` merged explicitly with base compose.

### 1) Prepare production environment

* Place a production `.env` on the host (never check it into git). Use strong secrets.
* Ensure a reverse proxy (Nginx) is configured (we provide `nginx/nginx.conf` as a starting point).
* Configure SSL (Let’s Encrypt, certbot, or a cloud load balancer). `nginx` container exposes 80/443.

### 2) Example commands (build + run)

Start by building `web` and `celery`, and running the other containers
```bash
# from project root: build and run prod stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

next time you can just run the stack without rebuilding (remove the --build)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
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
* __todo__: Add Sentry for bug monitoring.

# Settings & environment differences

* `kerya/settings/dev.py`: local developer configuration (DEBUG=True, local databases, useful logging).
* `kerya/settings/prod.py`: production configuration (DEBUG=False, secure settings, S3/MinIO endpoints using internal docker hostnames and ports, e.g. `db:5432` instead of `localhost:9905`).

---

# Troubleshooting

* **DB connection refused**: ensure Postgres container is healthy (`docker compose ps`) and your `.env` contains correct host/port. In dev, use mapped port `9905` or use `db:5432` if running Django inside Docker network.

---
