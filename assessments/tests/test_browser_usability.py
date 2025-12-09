import math
import os
import random
import time
from typing import Tuple

import pytest
from django.apps import apps
from django.contrib.auth.models import User
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BROWSERS = ["chrome", "firefox"]
SELENIUM_BROWSERS = ["chrome", "firefox"]

HOME_PATH = "/"
LOGIN_PATH = "/login/"
FORM_EMAIL_SELECTOR = "input[name='email']"
FORM_PASSWORD_SELECTOR = "input[name='password']"
FORM_SUBMIT_SELECTOR = "button[type='submit']"

LEVELS: dict[str, Tuple[int, Tuple[int, int], Tuple[int, int]]] = {
    "L1": (150, (30, 80), (4, 8)),
    "L2": (700, (30, 80), (4, 6)),
    "L3": (2000, (30, 100), (4, 6)),
}

LEVEL_NAV_THRESHOLDS_MS = {
    "L1": 4000,
    "L2": 7000,
    "L3": 12000,
}

HEADLESS = os.getenv("HEADLESS", "1") == "1"

pytestmark = pytest.mark.django_db


# --- Model helpers -------------------------------------------------------

def get_models():
    """Return the concrete model classes needed for seeding."""
    try:
        Course = apps.get_model("assessments", "Course")
        Team = apps.get_model("assessments", "Team")
        Enrollment = apps.get_model("assessments", "Enrollment")
        return Course, Team, Enrollment
    except Exception:
        return None, None, None


def _make_driver(browser_name: str):
    browser_name = browser_name.lower()
    try:
        if browser_name == "chrome":
            options = webdriver.ChromeOptions()
            if HEADLESS:
                options.add_argument("--headless=new")
                options.add_argument("--window-size=1366,900")
            return webdriver.Chrome(options=options)

        if browser_name == "firefox":
            options = webdriver.FirefoxOptions()
            if HEADLESS:
                options.add_argument("--headless")
            return webdriver.Firefox(options=options)

    except Exception:
        return None
    raise ValueError(f"Unsupported browser: {browser_name}")


@pytest.fixture(params=SELENIUM_BROWSERS, scope="class")
def selenium_browser(request):
    return request.param


@pytest.fixture(scope="class")
def driver(selenium_browser):
    drv = _make_driver(selenium_browser)
    if drv is None:
        pytest.skip(f"WebDriver for {selenium_browser} not available or not configured.")
    yield drv
    drv.quit()


@pytest.fixture(params=["L1", "L2", "L3"], scope="class")
def level_name(request):
    return request.param


@pytest.fixture(scope="class")
def level_config(level_name):
    return {
        "name": level_name,
        "courses": LEVELS[level_name][0],
        "students_range": LEVELS[level_name][1],
        "team_size_range": LEVELS[level_name][2],
        "nav_threshold_ms": LEVEL_NAV_THRESHOLDS_MS[level_name],
    }


@pytest.fixture(scope="class")
def login_user(db):
    user, created = User.objects.get_or_create(
        username="browser-tester@bc.edu",
        defaults={"email": "browser-tester@bc.edu", "first_name": "Browser", "last_name": "Tester"},
    )
    if created:
        user.set_password("test-pass-123")
        user.save()
    return user


@pytest.fixture(scope="class", autouse=True)
def seed_level_data(level_name, django_db_blocker):
    if os.getenv("SKIP_SEED", "0") == "1":
        return
    Course, Team, Enrollment = get_models()
    if not all([Course, Team, Enrollment]):
        pytest.skip("Expected Course, Team, and Enrollment models to exist.")

    with django_db_blocker.unblock():
        courses_target, students_range, team_size_range = LEVELS[level_name]
        existing = Course.objects.count()
        if existing >= courses_target:
            return

        remaining = courses_target - existing

        teacher, created = User.objects.get_or_create(
            username="seed-teacher@bc.edu",
            defaults={"email": "seed-teacher@bc.edu", "first_name": "Seed", "last_name": "Teacher"},
        )
        if created:
            teacher.set_password("teacher-pass-123")
            teacher.save()

        new_courses = [
            Course(
                name=f"Course {existing + i + 1}",
                course_code=f"C{existing + i + 1:05d}",
                year="2025",
                semester="Fall",
                description="Seeded course for browser usability checks.",
                created_by=teacher,
            )
            for i in range(remaining)
        ]
        Course.objects.bulk_create(new_courses, batch_size=250)
        new_courses = list(Course.objects.order_by("-id")[:remaining][::-1])

        for course in new_courses:
            n_students = random.randint(*students_range)
            team_min, team_max = team_size_range
            team_size = random.randint(team_min, team_max)

            students = [
                User(
                    username=f"student.{course.id}.{j}@bc.edu",
                    email=f"student.{course.id}.{j}@bc.edu",
                    first_name="Student",
                    last_name=str(course.id),
                )
                for j in range(n_students)
            ]
            User.objects.bulk_create(students, batch_size=500)
            students = list(User.objects.filter(username__startswith=f"student.{course.id}."))

            enrollments = [Enrollment(student=s, course=course) for s in students]
            Enrollment.objects.bulk_create(enrollments, batch_size=500)

            course_student_links = [Course.students.through(course_id=course.id, user_id=s.id) for s in students]
            Course.students.through.objects.bulk_create(course_student_links, batch_size=500)

            n_teams = max(1, math.ceil(n_students / team_size))
            teams = [Team(name=f"{course.course_code}-Team-{idx + 1}", course=course) for idx in range(n_teams)]
            Team.objects.bulk_create(teams, batch_size=200)
            teams = list(Team.objects.filter(course=course).order_by("id"))

            team_member_links = []
            through_model = Team.members.through
            for idx, student in enumerate(students):
                team = teams[idx % n_teams]
                team_member_links.append(through_model(team_id=team.id, user_id=student.id))
            through_model.objects.bulk_create(team_member_links, batch_size=500)


class TestBrowserUsability:
    def test_homepage_loads_and_has_title(self, live_server, driver, level_config):
        url = live_server.url + HOME_PATH
        driver.get(url)
        title = driver.title
        assert title, "Homepage should have a non-empty title"

    def test_layout_is_responsive_basic(self, live_server, driver, level_config):
        url = live_server.url + HOME_PATH
        driver.get(url)
        driver.set_window_size(1366, 800)
        time.sleep(0.2)
        width_desktop = driver.execute_script("return document.body.clientWidth;")

        driver.set_window_size(375, 812)
        time.sleep(0.2)
        width_mobile = driver.execute_script("return document.body.clientWidth;")
        assert width_desktop != width_mobile

    def test_key_navigation_and_focus(self, live_server, driver, level_config):
        url = live_server.url + HOME_PATH
        driver.get(url)
        body = driver.find_element(By.TAG_NAME, "body")
        start_active = driver.switch_to.active_element
        body.send_keys(Keys.TAB)
        time.sleep(0.1)
        after_tab = driver.switch_to.active_element
        assert start_active != after_tab

    def test_form_submit_smoke(self, live_server, driver, login_user, level_config):
        url = live_server.url + LOGIN_PATH
        driver.get(url)

        email_inputs = driver.find_elements(By.CSS_SELECTOR, FORM_EMAIL_SELECTOR)
        password_inputs = driver.find_elements(By.CSS_SELECTOR, FORM_PASSWORD_SELECTOR)
        submit_buttons = driver.find_elements(By.CSS_SELECTOR, FORM_SUBMIT_SELECTOR)
        if not email_inputs or not password_inputs or not submit_buttons:
            pytest.skip("Login form selectors not present on this page")

        email_inputs[0].clear()
        email_inputs[0].send_keys(login_user.email)
        password_inputs[0].clear()
        password_inputs[0].send_keys("test-pass-123")
        submit_buttons[0].click()

        WebDriverWait(driver, 5).until(EC.url_contains("/dashboard"))
        assert "/dashboard" in driver.current_url or "Welcome" in driver.page_source

    def test_no_obvious_js_errors_on_load(self, live_server, driver, level_config):
        driver.get(live_server.url + HOME_PATH)
        driver.execute_script(
            """
            window.__errors = [];
            window.addEventListener('error', function(e){ window.__errors.push(e.message || 'error'); });
            """
        )
        driver.get(live_server.url + HOME_PATH)
        time.sleep(0.2)
        errors = driver.execute_script("return window.__errors;") or []
        assert all("ReferenceError" not in e for e in errors), f"JS errors: {errors}"

    def test_navigation_perf_is_reasonable_for_level(self, live_server, driver, level_config):
        driver.get(live_server.url + HOME_PATH)
        time.sleep(0.2)
        nav_entry = driver.execute_script(
            """
            var e = (performance.getEntriesByType && performance.getEntriesByType('navigation')) || [];
            if (e && e.length) {
                var n = e[0];
                return {
                    dcl: n.domContentLoadedEventEnd,
                    start: n.startTime
                };
            }
            return null;
            """
        )

        if nav_entry and "dcl" in nav_entry and nav_entry["dcl"]:
            dcl_ms = float(nav_entry["dcl"])
        else:
            timing = driver.execute_script("return window.performance && performance.timing ? performance.timing : null;")
            if not timing:
                pytest.skip("No performance timing API available in this browser.")
            dcl_ms = float(timing.get("domContentLoadedEventEnd", 0) - timing.get("navigationStart", 0))

        threshold = level_config["nav_threshold_ms"]
        assert dcl_ms <= threshold, f"[{level_config['name']}] DOMContentLoaded {dcl_ms:.0f}ms > {threshold}ms"