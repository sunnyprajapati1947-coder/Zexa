---
name: docker-compose-generator
description: Generates production-ready docker-compose.yml files for multi-service applications. Use when containerizing an app with databases, caches, or other services.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: docker, compose, containers, postgres, redis, production
---

## Overview

Generates secure, production-oriented `docker-compose.yml` (and `docker-compose.override.yml` for local dev) with proper service definitions, networks, volumes, healthchecks, resource limits, environment variable management, secrets handling, and restart policies. Includes full examples for common stacks (Node.js + Postgres + Redis, Python + Postgres + Redis, etc.).

## When to Use This Skill

- Containerizing a new or existing multi-service application.
- The user says "docker-compose", "containerize", "local dev environment with DB", or "production docker setup".
- Setting up consistent environments across developer machines and CI/CD.

## Prerequisites

- Docker Desktop or Docker Engine + Compose V2 installed.
- Application code that can be containerized (Dockerfile exists or can be created).
- Understanding of the services needed (database, cache, queue, etc.).

## Steps

1. **Inventory all services** the app needs (app, db, cache, queue, search, etc.).

2. **Define networks**:
   - `frontend` (for reverse proxy / app).
   - `backend` (internal, for app ↔ db, app ↔ cache).

3. **Define volumes** for persistent data (named volumes preferred over bind mounts in production).

4. **Service definition template** (for each service):
   - `image` or `build`.
   - `environment` or `env_file` (never commit secrets in prod compose).
   - `volumes`.
   - `networks`.
   - `healthcheck` (critical).
   - `restart: unless-stopped`.
   - `deploy.resources` limits/requests (for Swarm or when using compose with limits).
   - `depends_on` with condition: service_healthy.

5. **Secrets & config**:
   - Use Docker secrets or external secret managers for prod.
   - For local: `.env` loaded via `env_file`.
   - Never put real credentials in the committed compose file.

6. **Healthchecks**:
   - DB: `pg_isready`, `mysqladmin ping`, etc.
   - App: `/health` endpoint that checks DB connectivity.

7. **Local vs prod**:
   - `docker-compose.yml` for prod-like.
   - `docker-compose.override.yml` (auto-loaded) for local dev (hot reload, different ports, debug flags).

8. **Output**:
   - Full `docker-compose.yml`.
   - Example `Dockerfile` for the app if missing.
   - `.env.example`.
   - Commands to bring up, view logs, run migrations, etc.
   - Production notes (use `docker compose up -d`, logging drivers, etc.).

## Examples

Complete `docker-compose.yml` for a Node.js + PostgreSQL + Redis + optional Nginx reverse proxy stack, with healthchecks, named volumes, proper networking, and a matching override for local development is included, along with the corresponding Dockerfiles and .env.example.

## Edge Cases & Error Handling

- **Database initialization**: Use `depends_on` + healthcheck, and an init container or entrypoint script that waits for DB.
- **Permission issues with volumes**: Run containers as non-root user; set correct UID/GID on volumes.
- **Secrets in CI**: Use GitHub Secrets or similar + `docker compose` with `--env-file` from secrets.
- **Scaling**: Note that some services (Postgres) are not easily horizontally scaled in compose; recommend managed DB for prod.

## Verification

1. `docker compose config` — validates syntax.
2. `docker compose up --build -d` — all services healthy (check `docker compose ps`).
3. App can connect to DB and Redis (test endpoints).
4. `docker compose down -v` cleans up.
5. Success: Environment is reproducible, services start reliably, data persists across restarts, and no secrets are in the repo.

## References

- [Docker Compose Specification](https://docs.docker.com/compose/compose-file/)
- [Compose Healthchecks](https://docs.docker.com/compose/compose-file/05-services/#healthcheck)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [Production Compose Guidance](https://docs.docker.com/compose/production/)
