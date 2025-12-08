# Security Testing Suite

## Test Results Summary

### What can you say about your system and the possibility of SQL injection and DoS attacks?

**SQL Injection - 🔴 CRITICAL VULNERABILITY:**
- **60 out of 120 tests FAILED (50% failure rate)**
- `/login/` endpoint: ALL 30 SQL injection payloads succeeded (100% vulnerable)
- `/admin/login/` endpoint: ALL 30 SQL injection payloads succeeded (100% vulnerable)
- Attackers can bypass authentication using simple payloads like `' OR '1'='1` or `admin'--`
- Database exposed to extraction (`UNION SELECT`), modification, and destruction (`DROP TABLE`)
- Search/query parameters are SECURE (properly using Django ORM)
- **Root cause:** Custom login forms likely use raw SQL queries instead of Django's ORM

**DoS Attacks - ✅ ACCEPTABLE (with limitations):**
- **4 out of 4 tests PASSED (100% pass rate)**
- Server never crashed under load testing
- Performance at different thread counts:
  - 10 threads: 1,280 req/s (excellent)
  - 50 threads: 880 req/s (good)
  - 100 threads: 800 req/s (degrading)
  - 200 threads: 62 req/s (95% throughput loss - vulnerable to slow DoS)
- No rate limiting detected - attackers can sustain 200+ connections to degrade service
- Single-threaded Django dev server is bottleneck
- **Verdict:** Relatively resistant to crashes but vulnerable to performance degradation attacks

**Authentication Bypass - 🟡 HIGH RISK:**
- 2 critical endpoints accessible without authentication:
  - `/dashboard/` - returns 200 (should require login)
  - `/assessments/` - returns 200 (should require login)
- Missing `@login_required` decorators on views

### What would you do differently in SE projects to guarantee security against these threats?

**Immediate Fixes (Critical):**
- ✅ Replace custom login with Django's built-in `AuthenticationForm` (uses parameterized queries)
- ✅ Add `@login_required` decorators to all protected views
- ✅ Install django-ratelimit for DoS protection (5 login attempts/min, 100 requests/hour per IP)
- ✅ Audit all `.raw()` and `cursor.execute()` calls - replace with Django ORM

**Best Practices for Future SE Projects:**
1. **Never build custom authentication** - always use framework-provided solutions (Django auth, Spring Security, etc.)
2. **Always use ORM, never raw SQL** - parameterized queries prevent 99% of SQL injection
3. **Security-first mindset from day 1:**
   - Define security requirements alongside functional requirements
   - Threat modeling before coding ("how could this be attacked?")
   - Code reviews with security checklist (no raw SQL, CSRF tokens, auth decorators, input validation)
4. **Defense in depth** - multiple security layers:
   - Input validation (reject SQL keywords in user input)
   - Application security (authentication, CSRF protection, rate limiting)
   - Database security (PostgreSQL with limited user permissions, no DROP/CREATE grants)
   - Infrastructure (WAF, DDoS protection, monitoring)
5. **Automated security testing in CI/CD:**
   - Run SQL injection tests on every commit
   - Security scanners (Bandit, Safety) block deployment if vulnerabilities found
   - Django `check --deploy` in pipeline
6. **Secure SDLC:**
   - Requirements: Identify sensitive data, define access controls
   - Design: Principle of least privilege, security architecture review
   - Implementation: Use framework features, never roll your own crypto/auth
   - Testing: Automated + manual penetration testing
   - Deployment: HTTPS enforced, secrets in environment variables
   - Maintenance: Quarterly security audits, weekly dependency scanning
7. **Team security culture:**
   - OWASP Top 10 review at project start
   - Regular security training sessions
   - Security champions in each team

**Key Lesson:** This project's vulnerabilities would have been prevented by simply using Django's built-in `AuthenticationForm` instead of custom login logic. Framework security features exist for a reason - use them.

---

## Overview

Comprehensive security testing framework for the PeerAssess Django application that tests for:
- **SQL Injection vulnerabilities** in login forms, search parameters, and form submissions
- **Authentication bypass** vulnerabilities via direct access to protected endpoints
- **Denial of Service (DoS)** vulnerabilities with concurrent request testing

## Files

1. **`sqli_testing_script.py`** - Main security testing framework with SecurityTester class
2. **`run_security_tests.py`** - Runner script that validates server availability before testing
3. **`SECURITY_TESTING.md`** - This documentation file

## Features

### SQL Injection Tests
- 30+ SQL injection payloads including:
  - Classic: `' OR '1'='1`, `admin'--`
  - UNION-based: `' UNION SELECT * FROM users--`
  - Time-based: `' WAITFOR DELAY '0:0:5'--`
  - Boolean-based: `' AND 1=1--`, `' AND 1=2--`
- Tests login endpoints, search parameters, and form submissions
- Detects SQL error leakage and successful injection attempts

### Authentication Bypass Tests
- Tests direct access to protected endpoints without authentication
- Validates proper redirect to login pages
- Checks for 401/403 responses on protected resources
- Endpoints tested:
  - `/dashboard/`
  - `/assessments/courses`
  - `/assessments/teams`
  - `/admin/`
  - User profile pages

### DoS Testing
- Progressive load testing with 10, 50, 100, and 200 concurrent threads
- Measures throughput, response times, and server degradation
- Configurable test duration (default: 5 seconds per test)
- Statistics: mean, p95 response times, requests per second

## Installation

No additional dependencies beyond the project's existing requirements:
```bash
# Activate virtual environment
source .venv/bin/activate

# Dependencies already installed from requirements.txt
# - requests
# - Standard library modules (threading, statistics, etc.)
```

## Usage

### Quick Start

1. **Start Django development server** (Terminal 1):
```bash
cd /Users/matthewlim/Desktop/In-delvelopment-1
source .venv/bin/activate
python manage.py runserver
```

2. **Run security tests** (Terminal 2):
```bash
cd /Users/matthewlim/Desktop/In-delvelopment-1
source .venv/bin/activate
python run_security_tests.py
```

### Advanced Usage

**Custom URL:**
```bash
python run_security_tests.py --url http://localhost:8000
```

**Verbose output:**
```bash
python run_security_tests.py --verbose
```

**Direct script usage:**
```bash
python sqli_testing_script.py
```

### Command Line Options

```
--url <url>      Specify custom base URL (default: http://127.0.0.1:8000)
--verbose        Enable verbose real-time output during testing
--help           Show help message
```

## Output

### Console Output
Real-time test execution with pass/fail indicators:
```
[17:30:15] ✓ SQLi Login - Username: ' OR '1'='1 - Status: 302, Vulnerable: False
[17:30:16] ✗ Auth Bypass: /dashboard/ - VULNERABLE - Accessible without auth!
```

### Report File
Automatically generates timestamped report: `security_test_report_YYYYMMDD_HHMMSS.txt`

**Report Sections:**
1. **Overall Summary** - Total tests, pass/fail counts, pass rate
2. **Results by Category** - Breakdown per test type
3. **Vulnerabilities Detected** - Detailed list of security issues
4. **Detailed Test Results** - Individual test outcomes with payloads
5. **Security Recommendations** - Actionable fixes

### Sample Report Output
```
======================================================================
SECURITY TEST REPORT
======================================================================
Generated: 2025-11-10 17:30:45
Target: http://127.0.0.1:8000
======================================================================

OVERALL SUMMARY
----------------------------------------------------------------------
Total Tests:     245
Passed:          223 (91.0%)
Failed:          22 (9.0%)

======================================================================
RESULTS BY CATEGORY
======================================================================

SQL Injection
----------------------------------------------------------------------
Total Tests:     180
Passed:          175
Failed:          5
Avg Response:    245ms

⚠️  VULNERABILITIES DETECTED (5):
  • SQLi Login - Username: ' OR '1'='1
    Endpoint: /login/
    Payload: ' OR '1'='1
    Details: Status: 302, Vulnerable: True [SECURITY RISK DETECTED!]
...
```

## Test Categories

### 1. SQL Injection (180+ tests)
- **Login Forms** (60 tests)
  - Tests username and email fields
  - All major SQL injection techniques
  - CSRF token extraction and submission
  
- **Search Parameters** (120 tests)
  - Query string injection
  - Search field injection
  - URL parameter manipulation

### 2. Authentication Bypass (6 tests)
- Protected dashboard endpoints
- Course management pages
- Team pages
- Admin interface
- User profile pages

### 3. Denial of Service (4 tests)
- 10 concurrent threads × 5 seconds
- 50 concurrent threads × 5 seconds
- 100 concurrent threads × 5 seconds
- 200 concurrent threads × 5 seconds

**Total: 190+ individual security tests**

## Security Best Practices

### If Vulnerabilities Are Found

**SQL Injection:**
```python
# ❌ NEVER do this:
query = f"SELECT * FROM users WHERE username='{user_input}'"

# ✅ Use Django ORM:
User.objects.filter(username=user_input)

# ✅ Or parameterized queries:
cursor.execute("SELECT * FROM users WHERE username=%s", [user_input])
```

**Authentication Bypass:**
```python
# ✅ Use decorators on views:
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    # Protected view logic
    pass
```

**DoS Protection:**
```python
# Install django-ratelimit
pip install django-ratelimit

# Apply rate limiting:
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/h')
def api_endpoint(request):
    pass
```

## Interpreting Results

### Pass Criteria
- ✓ **SQL Injection:** No successful authentication or SQL errors exposed
- ✓ **Auth Bypass:** Returns 302 (redirect to login), 401, or 403
- ✓ **DoS:** Server maintains reasonable response times (p95 < 10s)

### Fail Criteria
- ✗ **SQL Injection:** Successful login or SQL error messages in response
- ✗ **Auth Bypass:** 200 OK on protected endpoint without authentication
- ✗ **DoS:** Server severely degraded (p95 > 10s) or extremely low throughput

## Warning

⚠️ **IMPORTANT LEGAL NOTICE:**

These tests perform aggressive security scanning including:
- SQL injection attempts
- Authentication bypass attempts
- High-volume concurrent requests (DoS simulation)

**ONLY run these tests on:**
- Your own development/test environment
- Systems you own or have explicit written permission to test

**DO NOT run on:**
- Production systems (may cause downtime)
- Third-party systems without permission (illegal)
- Shared hosting environments

Unauthorized security testing may violate:
- Computer Fraud and Abuse Act (CFAA)
- Computer Misuse Act
- Local cybercrime laws

## Limitations

1. **Not a Complete Security Audit** - These tests cover common vulnerabilities but don't replace professional penetration testing
2. **False Negatives** - Some vulnerabilities may not be detected
3. **Development Server Only** - DoS tests assume single-threaded dev server
4. **No XSS Testing** - Cross-Site Scripting not currently tested
5. **No CSRF Testing** - Only verifies token presence, not validation

## Future Enhancements

Potential additions:
- Cross-Site Scripting (XSS) tests
- CSRF token validation tests
- File upload vulnerabilities
- Session management tests
- Password strength validation
- API endpoint security
- Header injection tests
- XML/JSON injection tests

## Troubleshooting

**Server not accessible:**
```bash
# Check if Django is running:
curl http://127.0.0.1:8000/

# Start server:
python manage.py runserver
```

**Import errors:**
```bash
# Make sure you're in the virtual environment:
source .venv/bin/activate

# Verify requests is installed:
pip install requests
```

**Permission denied:**
```bash
# Make scripts executable:
chmod +x sqli_testing_script.py run_security_tests.py
```

## Example Workflow

```bash
# Terminal 1: Start Django
cd /Users/matthewlim/Desktop/In-delvelopment-1
source .venv/bin/activate
python manage.py runserver

# Terminal 2: Run security tests
cd /Users/matthewlim/Desktop/In-delvelopment-1
source .venv/bin/activate
python run_security_tests.py --verbose

# Review report
cat security_test_report_*.txt

# Fix vulnerabilities based on recommendations

# Re-run tests to verify fixes
python run_security_tests.py
```

## Contact & Support

For issues or questions:
1. Review the generated report's recommendations
2. Check Django security documentation: https://docs.djangoproject.com/en/5.1/topics/security/
3. Review OWASP Top 10: https://owasp.org/www-project-top-ten/

---

**Created:** November 10, 2025  
**Version:** 1.0  
**Framework:** Django 5.1.7  
**Python:** 3.11+
