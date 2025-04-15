# Ctrl-Alt-Elite

## Project Overview

This is a Django-based web application for peer assessment, allowing professors to create courses, form student teams, and conduct peer evaluations.

## Development Environment

This project uses a Python virtual environment with the following versions:

- Python: 3.11.6
- Django: 5.1.7
- google-auth-oauthlib: 1.2.1

To ensure compatibility, please make sure your virtual environment matches these versions.

### Setting up your environment

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install django google-auth-oauthlib`
5. check for Python, Django, google-auth-oauthlib versions
    - `python --version`
    - `django --version`
    - `pip show google-auth-oauthlib`
6. run migrations: `python manage.py migrate`
7. start the development server: `python manage.py runserver`

### To Run Background Scheduler Locally
1. Make sure redis, celery_beat is installed by running `pip install celery redis django-celery-beat`
2. Install and run redis locally
    - Install redis by using the command `brew install redis`
    - Run a redis server by using the command `brew services start redis`
    - You can check if Redis is activated by running `redis-cli ping` which should give you the value `PONG`
3. Open 3 terminal windows
    - In the first window, run the command `bash celery -A PeerAssess worker --loglevel=info` to run the celery worker
    - In another window, run the command `bash celery -A PeerAssess beat --loglevel=info` to run the celery beat
    - In the final window, run `python manage.py runserver` and go to the admin page to add scheduled tasks 

## Project Structure

### PeerAssess (Project Directory)

`PeerAssess` is the main Django project directory containing:

- **settings.py** - Project configuration (database, apps, middleware, etc.)
- **urls.py** - URL declarations for the project
- **__init__.py** - Empty file that marks this directory as a Python package

### App Structure (To be created)

#### users
Handles user authentication and profile management:
- Google OAuth integration (restricted to BC emails)
- User roles (professor/student)
- User profiles and authentication

#### courses
Manages course and team organization:
- Course creation with year, semester, and group/team information
- Student invitation system
- Team management functionality

#### assessments
Handles the core peer assessment functionality:
- Assessment creation with publication and closing dates
- Question management (Likert scale and open-ended questions)
- Assessment submission and results visualization
- Email notification system

## Project Relationship

The **PeerAssess project** is the overall web application container that includes multiple apps.
Each app is a self-contained module implementing specific functionality:
- **users app**: Authentication and user management
- **courses app**: Course and team organization
- **assessments app**: Peer assessment functionality

## Key Features

- BC-restricted Google OAuth login
- Professor/student role differentiation
- Course and team management
- Customizable peer assessments (Likert scale and open-ended questions)
- Automated email notifications
- Anonymous feedback display
- Assessment result visualization

