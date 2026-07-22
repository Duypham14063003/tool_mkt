# SocialScope Dashboard

Monolithic Flask dashboard that connects Facebook Pages and TikTok accounts, stores encrypted OAuth credentials in MySQL, and displays normalized performance analytics with Chart.js.

## Setup

Requirements: Python 3.10+, MySQL 8+, a Meta app, and a TikTok developer app.

### Start MySQL with Docker

Copy the example environment once, then start the database:

```bash
cp .env.example .env
docker compose up -d db
docker compose ps
```

The Compose service publishes MySQL on local port `3307` by default to avoid conflicting with an existing MySQL installation. On the first start, MySQL automatically creates the `social_dashboard` database, application user, tables, indexes, and foreign key using `docker/mysql/init/001-schema.sql`. Data persists in the `social_dashboard_mysql` volume.

After the database reports `healthy`, run Flask on the host so Playwright can open the interactive Chrome window:

```bash
source .venv/bin/activate
flask --app app run --debug
```

To stop MySQL without deleting data:

```bash
docker compose down
```

To intentionally delete the local database and recreate it from the initialization SQL:

```bash
docker compose down -v
docker compose up -d db
```

`docker compose down -v` permanently deletes local database data; do not use it when the volume contains data you need.

```bash
cd social_dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the generated Fernet key in `TOKEN_ENCRYPTION_KEY`. Create the database and a least-privilege application user:

```sql
CREATE DATABASE social_dashboard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'social_dashboard'@'localhost' IDENTIFIED BY 'strong-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON social_dashboard.* TO 'social_dashboard'@'localhost';
```

Update `.env`, then initialize and run the app:

```bash
flask --app app init-db
flask --app app run --debug
```

Open `http://localhost:5000`. For a production process:

```bash
FLASK_ENV=production gunicorn --workers 3 --bind 0.0.0.0:8000 'app:create_app()'
```

Run behind HTTPS and a reverse proxy in production. Set `SESSION_COOKIE_SECURE=true`; production startup rejects the default secret and a missing encryption key. Keep the Fernet key stable and in a secrets manager because changing it makes stored tokens unreadable.

## OAuth app configuration

- Meta: add the exact `FACEBOOK_REDIRECT_URI` as a valid OAuth redirect URI. Request `pages_show_list`, `pages_read_engagement`, and `read_insights`; production use may require Meta App Review. The first Page returned by `/me/accounts` is connected.
- TikTok: register the exact `TIKTOK_REDIRECT_URI` and enable Login Kit with `user.info.basic` and `video.list`. TikTok refresh tokens are rotated when the provider returns a replacement.

Provider permissions and available insight fields depend on account type and app approval. API failures are returned to the browser as normalized `502` JSON responses without exposing credentials.

## Routes

| Route | Purpose |
| --- | --- |
| `GET/POST /login` | Session login |
| `POST /register` | Local account creation |
| `GET /auth/facebook` | Meta OAuth start |
| `GET /auth/facebook/callback` | Meta OAuth callback |
| `GET /auth/tiktok` | TikTok OAuth start |
| `GET /auth/tiktok/callback` | TikTok OAuth callback |
| `GET /api/v1/stats/facebook` | Normalized Facebook stats |
| `GET /api/v1/stats/tiktok` | Normalized TikTok stats |
| `GET /health` | Process health check |

Schema changes after initial deployment should be managed with Alembic/Flask-Migrate rather than `db.create_all()`.
# tool_mkt
