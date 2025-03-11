# Ctrl-Alt-Elite

## Project Overview

This is a Django-based web application for peer assessment, allowing professors to create courses, form student teams, and conduct peer evaluations.

## Project Structure

### PeerAssess (Project Directory)

`PeerAssess` is the main Django project directory containing:

- **settings.py** - Project configuration (database, apps, middleware, etc.)
- **urls.py** - URL declarations for the project
- **wsgi.py** - Entry point for WSGI-compatible web servers
- **asgi.py** - Entry point for ASGI-compatible web servers
- **__init__.py** - Empty file that marks this directory as a Python package

### App Structure

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

## Getting Started

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install django google-auth-oauthlib`
5. Create necessary apps:
   - `python manage.py startapp users`
   - `python manage.py startapp courses`
   - (assessments app already exists)
6. Update settings.py to include new apps
7. Run migrations: `python manage.py migrate`
8. Start the development server: `python manage.py runserver`

## Key Features

- BC-restricted Google OAuth login
- Professor/student role differentiation
- Course and team management
- Customizable peer assessments (Likert scale and open-ended questions)
- Automated email notifications
- Anonymous feedback display
- Assessment result visualization