# Ctrl-Alt-Elite

A Django-based peer assessment platform tailored for Boston College courses. The system lets professors create and manage courses, organize students into teams, collect peer assessments, and share results. Authentication is handled through Google OAuth and the application can send notifications through the Gmail API and scheduled Celery tasks.

## Table of Contents
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuring Google Login & Gmail](#configuring-google-login--gmail)
  - [1. Create Google OAuth credentials](#1-create-google-oauth-credentials)
  - [2. Register the credentials with Django](#2-register-the-credentials-with-django)
  - [3. Generate a shared Gmail API token](#3-generate-a-shared-gmail-api-token)
  - [4. Test email delivery](#4-test-email-delivery)
  - [Optional: Per-user Gmail tokens](#optional-per-user-gmail-tokens)
- [Running Background Tasks](#running-background-tasks)
- [Using the Application](#using-the-application)
  - [Logging in](#logging-in)
  - [Professor workflow](#professor-workflow)
  - [Student workflow](#student-workflow)
- [Management Commands](#management-commands)
- [Testing & Quality Checks](#testing--quality-checks)
- [Deployment Notes](#deployment-notes)
- [Troubleshooting](#troubleshooting)

## Key Features
- **BC email-restricted authentication** via Google OAuth, enforced by custom middleware and adapters.
- **Role-aware dashboard** with quick actions for professors and students.
- **Course management** including creation, enrollment codes, and student invitations.
- **Team management tools** for assigning students to teams and editing rosters.
- **Assessment builder** with Likert and open-ended questions, scheduling, and publishing controls.
- **Automated emails** for invitations, reminders, and published results via the Gmail API.
- **Background processing** powered by Celery and Redis for scheduled reminders.

## Architecture Overview
```
Ctrl-Alt-Elite/
├── PeerAssess/              # Django project settings, Celery config, URLs
├── assessments/             # Course, assessment, and invitation models & views
├── authentication/          # Google OAuth adapters, Gmail API helpers, middleware
├── templates/               # Django templates (dashboard, courses, assessments, login, etc.)
├── static/                  # Front-end assets (CSS/JS)
├── requirements.txt         # Python dependencies
├── google_oauth_client.json # (sample) OAuth client definition
├── gmail_tokens.json        # (sample) Gmail API tokens
└── manage.py                # Django entry point
```

The default development configuration uses SQLite. `PeerAssess/settingsprod.py` contains a production-ready configuration targeting PostgreSQL, Gunicorn, and environment-driven secrets.

## Prerequisites
- Python **3.11**
- `pip` and `virtualenv` (or `pyenv` / `conda`)
- Redis (for Celery background jobs)
- Google Cloud project with OAuth 2.0 and Gmail API access

## Quick Start
1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-org>/Ctrl-Alt-Elite.git
   cd Ctrl-Alt-Elite
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate        # On Windows use: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Create a local environment file (recommended)**
   Create a `.env` file in the project root for secrets used by `settingsprod.py` and background jobs:
   ```env
   SECRET_KEY=change-me
   DEFAULT_FROM_EMAIL=your-email@bc.edu
   EMAIL_HOST_USER=your-email@bc.edu
   EMAIL_HOST_PASSWORD=your-app-password-or-placeholder
   USE_GMAIL_API=True
   DB_PASSWORD=your-postgres-password-if-used
   ```
   The development settings (`PeerAssess/settings.py`) ship with placeholder credentials so the site can boot locally, but you should always supply your own secrets before deploying.

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **(Optional) Seed demo data**
   Populate the database with a sample course, team, assessment, and submissions. Include your Django username so the sample course recognizes you.
   ```bash
   python manage.py populate_test_data --current-user <your-username>
   ```

7. **Create an admin user**
   ```bash
   python manage.py createsuperuser
   ```

8. **Start the development server**
   ```bash
   python manage.py runserver
   ```
   Visit <http://localhost:8000/> to access the application.

## Configuring Google Login & Gmail
The platform relies on Google OAuth for authentication and the Gmail API for outbound mail. The sample `google_oauth_client.json` and `gmail_tokens.json` in this repository are placeholders—create your own credentials before using the app outside of a sandbox.

### 1. Create Google OAuth credentials
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or reuse an existing one) and enable the **Google+ API** (for profile/email) and **Gmail API**.
3. Configure the OAuth consent screen. Add `@bc.edu` to the list of allowed domains if you are restricting sign-ins to Boston College.
4. Create **OAuth 2.0 Client IDs → Web application** with the following redirect URIs:
   - `http://localhost:8000/accounts/google/login/callback/`
   - Additional production domains as needed (e.g., `https://your-domain/accounts/google/login/callback/`).
5. Download the JSON and save it to the project root as `google_oauth_client.json` (or any path referenced by `GOOGLE_OAUTH2_CLIENT_SECRETS_JSON`).

### 2. Register the credentials with Django
Load the OAuth client ID and secret into Django Allauth. Run this anytime you regenerate credentials.
```bash
python manage.py setup_google_oauth --client_id <your-client-id> --client_secret <your-client-secret>
```
The command configures the default `Site` entry (`localhost:8000`) and stores the OAuth client on the `allauth` `SocialApp` model.

### 3. Generate a shared Gmail API token
The application ships with a Gmail API email backend (`authentication.gmail_api.GmailAPIBackend`) that reads credentials from `gmail_tokens.json`. Generate a new token tied to the same Google account used in `DEFAULT_FROM_EMAIL`.
```bash
python manage.py setup_gmail_api --client-secrets google_oauth_client.json --token-file gmail_tokens.json
```
Follow the browser prompts to grant access. The command stores the access and refresh tokens so the app can send email without user interaction.

### 4. Test email delivery
Use the built-in management command to verify Gmail API access.
```bash
python manage.py test_email --to your.address@bc.edu
```
You can also hit the `/assessments/test-email/` endpoint while logged in to trigger a Gmail API test message.

### Optional: Per-user Gmail tokens
Professors can send mail using their own Gmail accounts. When a professor logs in via Google, Allauth stores their access and refresh tokens. Helpful commands for managing those tokens:
- `python manage.py check_gmail_tokens` — audit which professor accounts have valid tokens.
- `python manage.py force_refresh_token --email faculty@bc.edu --revoke` — revoke and delete stored tokens to force re-consent.
- `python manage.py reset_oauth_tokens --email faculty@bc.edu` — delete tokens for specific users so they must log in again.

If a professor does not have a valid token the system falls back to the shared Gmail API credentials defined above.

## Running Background Tasks
Celery powers reminders and closing routines. Launch Redis, the worker, and the beat scheduler while the Django server is running.

1. **Start Redis** (choose one):
   ```bash
   # Option A: brew
   brew services start redis

   # Option B: Docker
   docker run --name peerassess-redis -p 6379:6379 redis:7
   ```
2. **Run Celery worker**
   ```bash
   celery -A PeerAssess worker --loglevel=info
   ```
3. **Run Celery beat**
   ```bash
   celery -A PeerAssess beat --loglevel=info
   ```

Celery uses the broker/result URLs defined in `PeerAssess/settings.py` (`redis://localhost:6379/0`).

## Using the Application
### Logging in
1. Visit <http://localhost:8000/> and click **Sign In**.
2. Choose a role (Student or Professor) on the login form. The selection is stored in the session and saved to the `UserProfile` after a successful OAuth login.
3. Authenticate with a Boston College Google account. Non-`@bc.edu` addresses are rejected by `BCEmailMiddleware`. During local development with `DEBUG=True` you can reach `/debug/test_login` to create a non-BC test account.

### Professor workflow
1. **Create or manage a course** from the dashboard. Each course stores a code, semester, description, and enrollment code.
2. **Invite students** via `/assessments/invite-students/` by pasting BC email addresses or share the enrollment code.
3. **Organize teams** with `/assessments/<course>/add_teams`, assigning enrolled students to teams or editing existing rosters.
4. **Build assessments** using `/assessments/create_peer_assessments/`. Define open/due dates plus Likert and open-ended questions.
5. **Monitor submissions** from the course detail page, publish results, and optionally send reminders using the Celery-powered notifications.
6. **Publish results** when ready; students are notified by email and can view aggregated feedback and scores.

### Student workflow
1. **Accept an invitation** from the email or visit `/assessments/pending-invitations/` to accept/decline outstanding invites. Students can also enroll with a course code.
2. **View active assessments** on the dashboard and open each assessment to evaluate teammates. Progress can be saved mid-assessment.
3. **Submit peer reviews** for every teammate. Unique constraints ensure one submission per teammate per assessment.
4. **View published results** once professors release them via `/assessments/assessment/<id>/results/` or the dashboard shortcut.

## Management Commands
| Command | Purpose |
|---------|---------|
| `setup_google_oauth` | Register Google OAuth client ID/secret with Django Allauth. |
| `setup_gmail_api` / `debug_gmail_setup` | Generate Gmail API tokens and verify scopes. |
| `test_email` | Send a Gmail API test message using the configured backend. |
| `populate_test_data` | Create sample professor/student accounts, a course, teams, and an assessment. |
| `send_publication_emails` | Email students when a `PeerAssessment` publication date is reached. |
| `send_warning_emails` | Warn students who have not submitted when deadlines approach. |
| `check_gmail_tokens` | Audit stored professor Gmail tokens. |
| `force_refresh_token`, `force_reauth_google`, `reset_oauth_tokens`, `create_test_token` | Utilities for managing OAuth token lifecycles during troubleshooting. |

Run any command with `python manage.py <command> --help` to see additional options.

## Testing & Quality Checks
- Run Django’s unit test suite:
  ```bash
  python manage.py test
  ```
- (Optional) Use pylint/isort for static analysis, both available in `requirements.txt`.

## Deployment Notes
- Use `PeerAssess/settingsprod.py` (set `DJANGO_SETTINGS_MODULE=PeerAssess.settingsprod`) for production. It expects:
  - Environment-driven `SECRET_KEY`, email credentials, and Postgres password.
  - `DEBUG=False` and `ALLOWED_HOSTS` populated.
  - Static files collected via `python manage.py collectstatic`.
- Run the app under Gunicorn (`gunicorn PeerAssess.wsgi`) or another WSGI server.
- Configure HTTPS termination and set `CSRF_TRUSTED_ORIGINS` for your domain.
- Provision Redis in production to support Celery.

## Troubleshooting
| Symptom | Resolution |
|---------|------------|
| Non-BC email can’t log in | Confirm you used an `@bc.edu` account or disable the domain check in `authentication.adapters.BCEmailAdapter`. |
| Gmail API returns `invalid_grant` | Revoke the app at <https://myaccount.google.com/permissions> and rerun `setup_gmail_api` or `force_refresh_token`. |
| Email fails silently | Ensure `USE_GMAIL_API=True`, `gmail_tokens.json` exists, and the Celery worker logs do not show authentication failures. |
| Celery tasks never fire | Verify Redis is running, worker/beat processes are started, and scheduled tasks exist in Django admin (`django_celery_beat`). |
| Students can’t join a course | Confirm invitations were sent to the correct address or share the enrollment code from the course detail page. |

For additional insight, review debug views under `/debug/` and log output from Celery/Django during authentication and email flows.
