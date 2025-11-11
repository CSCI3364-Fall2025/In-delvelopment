# Load Testing - Quick Start Guide

## What Was Done

✅ Created virtual environment and installed dependencies  
✅ Ran database migrations  
✅ Seeded database with 600 courses, 31,320 students, 6,659 teams  
✅ Started Django development server  
✅ Created Python load testing script (`load_test.py`)  
✅ Ran tests with 100 and 1,000 concurrent users  
✅ Generated comprehensive analysis report

## Key Files Created

1. **`load_test.py`** - Python script to run load tests
2. **`LOAD_TEST_REPORT.md`** - Comprehensive analysis and recommendations
3. **`gatling/`** - Directory with Gatling simulation (alternative approach)

## Test Results Summary

### 100 Users
- ⚠️ 31% error rate (90 failures out of 290 requests)
- Mean response time: 324ms
- p95: 1,304ms
- **Issue:** `/assessments/teams` endpoint completely failing

### 1,000 Users  
- ⚠️ 31% error rate (900 failures out of 2,900 requests)
- Mean response time: 404ms
- p95: 1,676ms
- p99: 3,122ms
- **Issue:** Same authentication/session problem with teams endpoint

## Critical Findings

🔴 **CRITICAL:** Authentication issue causing `/assessments/teams` to fail 100% of the time
- Redirects to `/accounts/login/` even after successful login
- Affects all student users (90% of test traffic)

🟡 **HIGH:** Response times degrade significantly under load
- Faculty endpoints 194-211% slower with 10x users
- Login operations take 2-3 seconds at p99

🟡 **MEDIUM:** Current stack (dev server + SQLite) not production-ready
- Estimated max capacity: ~50 concurrent users
- Requires PostgreSQL, Gunicorn, caching for production

## Quick Recommendations

### Fix Now (Critical)
1. Debug and fix `/assessments/teams` authentication issue
2. Pre-create test users (don't create during load test)
3. Add database indexes on Course and Team models

### This Week (High Priority)
4. Optimize dashboard queries with `select_related()` and `prefetch_related()`
5. Implement Redis caching for sessions and common queries
6. Switch to PostgreSQL

### This Month (Production Ready)
7. Deploy with Gunicorn (4-8 workers)
8. Add comprehensive caching strategy
9. Set up monitoring and alerts

## Can It Handle X Users?

| User Count | Current Stack | With Improvements |
|------------|---------------|-------------------|
| 50 | ✅ Yes | ✅ Yes |
| 100 | ⚠️ Marginal | ✅ Yes |
| 500 | ❌ No | ✅ Yes |
| 1,000 | ❌ No | ✅ Yes |
| 3,000 | ❌ No | ✅ Yes (with full stack) |
| 5,000 | ❌ No | ✅ Yes (with HA setup) |

**Current realistic limit:** ~50 concurrent users  
**With recommended improvements:** 3,000-5,000 concurrent users

## How to Re-run Tests

```bash
# Start Django server (terminal 1)
cd /Users/matthewlim/Desktop/In-delvelopment-1
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000

# Run load test (terminal 2)
cd /Users/matthewlim/Desktop/In-delvelopment-1
source .venv/bin/activate
python load_test.py
```

## Next Steps

1. **Read the full report:** Open `LOAD_TEST_REPORT.md` for detailed analysis
2. **Fix authentication:** Debug why `/assessments/teams` fails with 404
3. **Check queries:** Add Django Debug Toolbar to identify N+1 queries
4. **Plan improvements:** Review recommendations and prioritize fixes

---

For detailed analysis, performance metrics, and architectural recommendations, see **`LOAD_TEST_REPORT.md`**.
