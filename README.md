# Ctrl-Alt-Elite

A Django-based peer assessment platform tailored for Boston College courses. The system lets professors create and manage courses, organize students into teams, collect peer assessments, and share results. Authentication now uses a simple email/password flow restricted to `@bc.edu` addresses.

## Table of Contents
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
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
- **BC email-restricted authentication** using a lightweight signup/login form enforced by custom middleware.
- **Role-aware dashboard** with quick actions for professors and students.
- **Course management** including creation, enrollment codes, and student invitations.
- **Team management tools** for assigning students to teams and editing rosters.
- **Assessment builder** with Likert and open-ended questions, scheduling, and publishing controls.
- **Automated emails** for invitations, reminders, and published results using Django's email framework.
- **Background processing** powered by Celery and Redis for scheduled reminders.

## Architecture Overview
```
Ctrl-Alt-Elite/
├── PeerAssess/              # Django project settings, Celery config, URLs
├── assessments/             # Course, assessment, and invitation models & views
├── authentication/          # Login/logout views, middleware, signals
├── templates/               # Django templates (dashboard, courses, assessments, auth)
├── static/                  # Front-end assets (CSS/JS)
├── requirements.txt         # Python dependencies
└── manage.py                # Django entry point
```

The default development configuration uses SQLite. `PeerAssess/settingsprod.py` contains a production-ready configuration targeting PostgreSQL, Gunicorn, and environment-driven secrets.

## Prerequisites
- Python **3.11**
- `pip` and `virtualenv` (or `pyenv` / `conda`)
- Redis (for Celery background jobs)

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
   EMAIL_HOST=your-smtp-host
   EMAIL_HOST_USER=your-email@bc.edu
   EMAIL_HOST_PASSWORD=your-app-password-or-placeholder
   EMAIL_PORT=587
   EMAIL_USE_TLS=true
   DB_PASSWORD=your-postgres-password-if-used
   SITE_URL=https://peerassess.online
   ```
   The development settings (`PeerAssess/settings.py`) use the console email backend, so no SMTP configuration is required for local testing.

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
2. Enter your Boston College email address and password. Accounts can be created from the **Sign Up** link on the login page.
3. During local development with `DEBUG=True` you can reach `/debug/test_login` to create a non-BC test account.

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
| `populate_test_data` | Create sample professor/student accounts, a course, teams, and an assessment. |
| `send_publication_emails` | Email students when a `PeerAssessment` publication date is reached. |
| `send_warning_emails` | Notify students about upcoming deadlines. |

## Testing & Quality Checks
Run Django's test suite before committing changes:
```bash
python manage.py test
```

## Deployment Notes
- Use `PeerAssess/settingsprod.py` for production deployments. It expects environment variables for database, email, and secret key configuration.
- Run migrations and collect static files during deployment:
  ```bash
  python manage.py migrate
  python manage.py collectstatic
  ```
- Configure a production-ready email backend (SMTP credentials) and set `SITE_URL` to your public domain.

## Troubleshooting
- **Forgotten password**: Reset the user via Django admin or the shell (`python manage.py shell`).
- **Email not sending**: Confirm SMTP credentials (in production) or check the development console output. The `/assessments/test-email/` endpoint triggers a test message to the logged-in user.
- **Background tasks not running**: Ensure Redis is running and both the Celery worker and beat scheduler processes are active.
