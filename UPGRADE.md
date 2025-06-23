# UPGRADE.md

This document outlines the steps required to upgrade the Japanese Lexical Graph project to use token-based authentication (JWT), PostgreSQL as the database, and SQLAlchemy as the ORM.

## 1. Dependencies

- Add `Flask-JWT-Extended` for token-based authentication
- Add `SQLAlchemy` (or `SQLModel`) for ORM
- Add `psycopg2-binary` for PostgreSQL driver
- Add `alembic` for database migrations

## 2. Configuration

- Update `.env` to include:
  ```env
  DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB_NAME
  SECRET_KEY=your-secret-key
  JWT_SECRET_KEY=your-jwt-secret-key
  ```
- Load these values in `config.py` using `python-dotenv`

## 3. Database Setup

- Install and run PostgreSQL locally or on your server
- Create a dedicated database for the application
- Verify connectivity via `DATABASE_URL`

## 4. Initialize SQLAlchemy

- Create a `db.py` (or update `app.py`) to initialize the SQLAlchemy engine and session
- Define a declarative `Base` for models

## 5. Models

- **User** model:
  - `id` (PK)
  - `username`, `email`
  - `password_hash`
  - `created_at`, `last_login`
- **InteractionLog** model:
  - `id` (PK)
  - `user_id` (FK to User)
  - `endpoint`, `payload` (JSON)
  - `timestamp`

## 6. Migrations

- Initialize Alembic with `alembic init alembic`
- Configure `alembic.ini` to use the `DATABASE_URL`
- Create and apply initial migrations for `User` and `InteractionLog`

## 7. Authentication Endpoints

- `POST /auth/signup`: register users, hash passwords with `passlib`
- `POST /auth/login`: verify credentials, return access & refresh tokens
- `POST /auth/refresh`: issue new access token using refresh token
- `POST /auth/logout`: revoke tokens (optional)
- `GET /auth/me`: return current user profile

## 8. Protecting Routes

- Use `@jwt_required()` to secure endpoints
- Handle errors to return HTTP 401 for unauthorized requests

## 9. Interaction Logging

- Implement middleware or decorator to log each authenticated request
- Record `user_id`, `endpoint`, request data, and `timestamp` in `InteractionLog`

## 10. Front-End Changes

- Add login & signup forms
- Store JWTs in HTTP-only cookies or `localStorage`
- Attach `Authorization: Bearer <token>` header on API requests
- Update UI to reflect authentication state

## 11. Testing

- Unit tests for signup/login logic and token handling
- Integration tests to verify access control (401 vs 200)
- Tests to ensure `InteractionLog` entries are created correctly

## 12. Deployment & Migration

- Add `alembic upgrade head` to deployment script
- Ensure `DATABASE_URL`, `SECRET_KEY`, and `JWT_SECRET_KEY` are set in production
- Securely manage and rotate secrets

---

> **Next Steps:**
> - Review and refine each section
> - Break tasks into `TASK.md` with sub-tasks for implementation 