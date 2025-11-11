Gatling load test for PeerAssess

Overview
- This folder contains a Gatling simulation that exercises the student dashboard and the faculty (course) dashboard.
- The simulation uses the debug `/test_login` endpoint to create a session for a user (DEBUG must be True in `PeerAssess/settings.py`).

How to run
1. Download Gatling OSS bundle from https://gatling.io/open-source/ and unpack it somewhere. The bundle provides a `bin/gatling.sh` script.
2. Copy this `gatling/` directory into the unpacked Gatling bundle root (so that `user-files/simulations/StudentFacultySimulation.scala` lives under the bundle's `user-files/simulations/`).

Example run commands (from Gatling bundle root):

# Run with 100 users ramping up over 30s
./bin/gatling.sh -s StudentFacultySimulation -Dusers=100 -DrampSeconds=30

# Run with 1000 users ramping up over 120s
./bin/gatling.sh -s StudentFacultySimulation -Dusers=1000 -DrampSeconds=120

Notes and prerequisites
- The Django app must be running and reachable at http://localhost:8000.
- You should seed data before running big tests: `python manage.py seed_data --level 2 --purge --fast-passwords --semester Fall --year 2025`. The command may require installing dependencies (see project `requirements.txt`).
- Ensure `DEBUG = True` in `PeerAssess/settings.py` so `/test_login` is available.

Interpreting results
- Gatling will produce an HTML report in `results/` (open in browser).
- Look for mean/median response times, 95th/99th percentiles, request per second throughput, and error counts.

Quick analysis checklist
- If mean response times < 500ms and 95th < 2s with few errors, that's generally good for interactive dashboards.
- If errors > 1% or p95 > 5s, investigate backend bottlenecks (DB queries, N+1, heavy template rendering) and static file serving.

Suggested follow-ups
- Add an endpoint-specific scenario that hits expensive API endpoints (e.g., `/assessments/api/team-submissions/...`).
- Add monitoring (APM, DB slow query logs) to capture actual bottlenecks under load.
- Run tests from multiple load generators to model real-world concurrency.
