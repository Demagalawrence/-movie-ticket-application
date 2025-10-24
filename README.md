# Movie Ticket Application (Django)

A Django-based movie ticket booking application. Uses SQLite for Django auth/admin and MongoDB (via MongoEngine) for application data. Integrates Stripe for payments and supports QR code generation for tickets.

## Prerequisites
- Python 3.11+ (recommended)
- Git
- MongoDB running locally on `mongodb://localhost:27017`
- (Optional) Virtual environment tool: `venv` or `virtualenv`

## Quick Start

1. Clone the repository
```bash
git clone https://github.com/<your-username>/movie-ticket-application.git
cd movie-ticket-application/movie_management_system
```

2. Create and activate a virtual environment
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Ensure MongoDB is running
```bash
# Default local dev (no auth)
# MongoDB should be available at: mongodb://localhost:27017
```

5. Apply Django migrations (SQLite for Django apps)
```bash
python manage.py migrate
```

6. (Optional) Create a superuser for Django admin
```bash
python manage.py createsuperuser
```

7. Run the development server
```bash
python manage.py runserver
```

- App will be available at: http://127.0.0.1:8000/
- Django admin at: http://127.0.0.1:8000/admin/

## Project Structure
```
movie-ticket-application/
├─ movie_management_system/
│  ├─ manage.py                   # Django CLI entrypoint
│  ├─ requirements.txt            # Python dependencies
│  ├─ db.sqlite3                  # SQLite DB (generated)
│  ├─ staticfiles/                # Collected static (generated)
│  ├─ sessions/                   # File-based sessions (generated)
│  ├─ movie_management_system/    # Django project config (settings/urls/wsgi/asgi)
│  └─ movieflex/                  # Main app (models/views/forms/templates/static)
└─ README.md
```

## Configuration
Current defaults (development):
- Django `DEBUG=True`, `ALLOWED_HOSTS=[]`
- SQLite database at `movie_management_system/db.sqlite3`
- MongoDB connection in `settings.py`:
  - `mongoengine.connect(db='movie_db', host='mongodb://localhost:27017')`
- Sessions are file-based at `movie_management_system/sessions/`
- Static files:
  - `STATIC_URL = /static/`
  - `STATIC_ROOT = <BASE>/staticfiles`
  - `STATICFILES_DIRS = [<BASE>/movieflex/static]`
- Stripe keys in `settings.py` (placeholders):
  - `STRIPE_SECRET_KEY = 'sk_test_your_secret_key_here'`
  - `STRIPE_PUBLISHABLE_KEY = 'pk_test_your_publishable_key_here'`

### Environment Variables (Recommended)
For production use, move secrets and config to environment variables and update `settings.py` accordingly.
Suggested variables:
- `SECRET_KEY`
- `DEBUG` ("False" for production)
- `ALLOWED_HOSTS` (comma-separated)
- `MONGODB_URI` (e.g., `mongodb://user:pass@host:27017/movie_db`)
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`

> Note: As shipped, `settings.py` uses hardcoded values. Consider refactoring to read from environment variables.

## Static Files
Collect static assets (mainly for production/testing static pipeline):
```bash
python manage.py collectstatic
```
Files will be gathered into `movie_management_system/staticfiles/`.

## Common Commands
- Start server: `python manage.py runserver`
- Make migrations (if Django models change): `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`
- Create admin: `python manage.py createsuperuser`
- Check Django config: `python manage.py check`

## Troubleshooting
- MongoDB connection errors: ensure MongoDB is running locally and accessible at `mongodb://localhost:27017`. If using a custom URI or credentials, update the connection in `settings.py`.
- Stripe: set real test keys in `settings.py` before testing payment flows.
- Static not loading: in development, ensure `DEBUG=True`. In production, serve static via a web server or CDN after `collectstatic`.
- Sessions path: verify that the `sessions/` folder exists and is writable (it is auto-created on startup).

## Production Notes
- Set `DEBUG=False`, configure `ALLOWED_HOSTS`, and secure cookies (`CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`) behind HTTPS.
- Do not commit real secrets. Use environment variables or a secrets manager.
- Use a proper WSGI/ASGI server (gunicorn/uvicorn+daphne) behind a reverse proxy.
- Use a persistent session backend (cache/DB) for multi-instance deployments.
- Configure MongoDB with credentials, TLS, and timeouts.

## License
Add your preferred license here (e.g., MIT).
