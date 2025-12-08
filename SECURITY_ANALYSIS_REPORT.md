# Security Analysis Report: SQL Injection and DoS Vulnerability Assessment

**Project:** PeerAssess - Peer Assessment Management System  
**Date:** December 8, 2025  
**Tests Executed:** 130 (120 SQL Injection, 6 Auth Bypass, 4 DoS)

---

## Executive Summary

Security testing revealed **critical vulnerabilities**:

- **SQL Injection:** 60/120 tests FAILED (50% failure rate) - 🔴 **CRITICAL**
- **Authentication Bypass:** 2/6 tests FAILED (33% failure rate) - 🟡 **HIGH RISK**  
- **DoS Resilience:** 4/4 tests PASSED (100% pass rate) - ✅ **ACCEPTABLE**

**Overall Security Grade: F - NOT PRODUCTION READY**

---

## Question 1: What Can You Say About Your System and SQL Injection/DoS Attacks?

### SQL Injection Vulnerabilities - 🔴 CRITICAL RISK

**Test Results:** 60 out of 120 tests failed (50% failure rate)

#### Vulnerable Endpoints:

**1. `/login/` - User Login (30/30 payloads succeeded)**
```
✗ ' OR '1'='1          → Bypassed authentication
✗ admin'--              → Bypassed authentication  
✗ ' UNION SELECT * FROM auth_user-- → Database access
✗ '; DROP TABLE users-- → Destructive command accepted
```

**Impact:** Attackers can:
- Log in as any user without credentials
- Extract entire user database
- Modify or delete data
- Gain admin privileges

**2. `/admin/login/` - Django Admin (30/30 payloads succeeded)**

Same vulnerability pattern - admin panel completely exposed to SQL injection.

**3. Search/Query Parameters - ✅ SECURE**

All dashboard and course search parameters properly rejected SQL injection attempts using Django ORM.

#### Root Cause:

The login forms likely use **raw SQL queries with string concatenation** instead of Django's ORM:

```python
# VULNERABLE (suspected current code):
query = f"SELECT * FROM auth_user WHERE email='{email}'"
cursor.execute(query)

# SECURE (should be):
user = User.objects.get(email=email)  # ORM uses parameterized queries
```

**Evidence:** Debug endpoints that use Django ORM properly rejected all 30 injection attempts. Only custom login forms are vulnerable.

---

### DoS (Denial of Service) Resilience - ✅ ACCEPTABLE

**Test Results:** 0 failures (100% pass rate)

| Threads | Throughput | p95 Response | Status |
|---------|------------|--------------|--------|
| 10 | 1,280 req/s | 10ms | ✅ Excellent |
| 50 | 880 req/s | 114ms | ✅ Good |
| 100 | 800 req/s | 252ms | ⚠️ Degrading |
| 200 | 62 req/s | 28ms | ⚠️ 95% throughput loss |

**Key Findings:**

**Strengths:**
- Server never crashed under load
- No timeout errors at any level
- Graceful degradation under extreme load

**Weaknesses:**
- Throughput drops 95% under high concurrency (200 threads)
- No rate limiting - attackers can sustain 200+ connections to degrade service
- Single-threaded Django dev server is the bottleneck
- Authenticated endpoints even more vulnerable (from load tests: 31% error rate at 100 users)

**Conclusion on DoS:** System is **moderately resistant** to crashes but **vulnerable to performance degradation attacks**. An attacker maintaining 200 concurrent connections would make the system nearly unusable (62 req/s vs normal 1,280 req/s).

---

### Authentication Bypass - 🟡 HIGH RISK

**2 critical endpoints accessible without login:**

```
✗ /dashboard/     → Returns 200 (should redirect to login)
✗ /assessments/   → Returns 200 (exposes assessment data)
```

**Cause:** Missing `@login_required` decorators on view functions.

---

## Question 2: What Would You Do Differently in SE Projects?

### Immediate Fixes for This Project (Critical - Do First)

#### 1. Replace Custom Login with Django's Built-in Authentication

**Fix in `authentication/views.py`:**
```python
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})
```

**Why this works:**
- Django's `AuthenticationForm` uses parameterized queries (prevents SQL injection)
- Automatic CSRF protection
- Secure password verification with `check_password()`
- Session management handled securely

**Estimated time:** 2 hours

#### 2. Add Authentication Decorators

**Fix in `assessments/views.py`:**
```python
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    # existing code
    
@login_required  
def assessments_list(request):
    # existing code
```

**Estimated time:** 10 minutes

#### 3. Add Rate Limiting (DoS Protection)

**Install and configure:**
```bash
pip install django-ratelimit
```

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')  # 5 login attempts per minute
def login_view(request):
    # login code
    
@ratelimit(key='ip', rate='100/h')  # 100 requests per hour per IP
@login_required
def dashboard(request):
    # dashboard code
```

**Estimated time:** 3 hours

---

### Best Practices for Future SE Projects

#### 1. Security-First Development from Day 1

**NEVER build custom authentication/authorization:**
- ❌ Don't: Write custom SQL queries for login
- ✅ Do: Use framework-provided authentication (Django, Spring Security, etc.)
- ✅ Do: Use ORM/prepared statements for ALL database queries

**Principle:** Frameworks have security built-in and tested by thousands of developers. Custom code introduces vulnerabilities.

#### 2. Always Use ORM, Never Raw SQL

**Rule:** If you type `cursor.execute()` or `objects.raw()`, you're probably doing it wrong.

```python
# ❌ DANGEROUS - Never do this
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# ✅ SAFE - Always do this  
User.objects.filter(name=user_input)
```

#### 3. Defense in Depth

Implement multiple security layers:

**Layer 1 - Input Validation:**
- Validate all user input at form level
- Reject suspicious patterns (SQL keywords, special characters)

**Layer 2 - Application Security:**
- Authentication required on all sensitive endpoints
- CSRF tokens on all forms
- Rate limiting on login/API endpoints

**Layer 3 - Database Security:**
- Use PostgreSQL with limited user permissions (not SQLite in production)
- Database user cannot DROP tables
- Connection over SSL

**Layer 4 - Infrastructure:**
- WAF (Web Application Firewall) to filter malicious requests
- DDoS protection (Cloudflare, AWS Shield)
- Server monitoring and alerting

#### 4. Automated Security Testing in CI/CD

**Add to every project's pipeline:**

```yaml
# .github/workflows/security.yml
- name: Run security checks
  run: |
    python manage.py check --deploy
    bandit -r .
    safety check
    python run_security_tests.py
```

**Benefits:**
- Catch vulnerabilities before they reach production
- Every commit is security tested
- Failed security tests block deployment

#### 5. Secure SDLC (Software Development Lifecycle)

**Requirements Phase:**
- Define security requirements alongside functional requirements
- Identify sensitive data (passwords, PII, financial data)
- Threat modeling: "How could this be attacked?"

**Design Phase:**
- Security architecture review
- Principle of least privilege (users only get minimum necessary access)
- Plan authentication/authorization strategy

**Implementation Phase:**
- Code reviews with security focus
- Never use deprecated/insecure libraries
- Keep dependencies updated

**Testing Phase:**
- Automated security tests (SQL injection, XSS, CSRF)
- Manual penetration testing for critical systems
- Load testing to find DoS vulnerabilities

**Deployment Phase:**
- Security headers configured (HTTPS, CSP, X-Frame-Options)
- Secrets in environment variables (never in code)
- Rate limiting and monitoring enabled

**Maintenance Phase:**
- Regular security audits (quarterly)
- Dependency vulnerability scanning (weekly)
- Security patch application (within 48 hours)

#### 6. Security Training and Culture

**For every SE project:**
- Team review of OWASP Top 10 at project start
- Security champions in each team
- Regular "lunch and learn" sessions on security topics

**Code review checklist:**
```markdown
- [ ] No raw SQL with user input
- [ ] All forms have CSRF tokens
- [ ] Authentication on sensitive endpoints
- [ ] Input validation on all user data
- [ ] No secrets in code (use env vars)
```

---

## Summary and Recommendations

### Current State:
- 🔴 **SQL Injection:** System is completely vulnerable - attackers can access any account
- 🟡 **Auth Bypass:** 2 critical endpoints missing authentication
- ✅ **DoS:** Relatively resistant but needs rate limiting

### Critical Actions (This Week):
1. Replace custom login with Django `AuthenticationForm` (2 hours)
2. Add `@login_required` decorators to dashboard and assessments (10 min)
3. Install django-ratelimit for DoS protection (3 hours)
4. Audit all database queries for raw SQL usage (4 hours)

**Total effort:** ~2 days to fix critical vulnerabilities

### Key Lessons for Future Projects:
1. **Never build custom auth** - use framework security features
2. **Always use ORM** - prevents 99% of SQL injection attacks
3. **Security from day 1** - not an afterthought
4. **Automate security testing** - in CI/CD pipeline
5. **Defense in depth** - multiple security layers
6. **Regular audits** - continuous security assessment

### Path to Production:
- **Week 1:** Fix SQL injection and auth bypass (critical)
- **Week 2:** Add rate limiting, input validation, security headers
- **Week 3:** Migrate to PostgreSQL, comprehensive testing
- **Week 4:** Security audit, penetration testing
- **After 1 month:** Production-ready with monitoring

---

**Overall Assessment:** The system has critical vulnerabilities that make it unsuitable for production. However, all issues are fixable within 2-4 weeks using Django's built-in security features.

**Prepared by:** Security Testing Framework v1.0  
**Date:** December 8, 2025
