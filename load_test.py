#!/usr/bin/env python3
"""
Load testing script for PeerAssess dashboards using Python requests.
Alternative to Gatling when network downloads are restricted.
"""
import time
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List
import requests

BASE_URL = "http://localhost:8000"
DEBUG = False


@dataclass
class RequestResult:
    """Store result of a single HTTP request"""
    url: str
    duration_ms: float
    status_code: int
    success: bool
    error: str = ""


def login_as_role(session: requests.Session, role: str, email: str) -> bool:
    """Login via the debug test_login endpoint"""
    try:
        # Get CSRF token
        resp = session.get(f"{BASE_URL}/debug/test_login", timeout=10)
        if resp.status_code != 200:
            return False
        
        # Extract CSRF token from HTML
        csrf_token = None
        for line in resp.text.split('\n'):
            if 'csrfmiddlewaretoken' in line and 'value' in line:
                # Try double quotes first
                if 'value="' in line:
                    start = line.find('value="') + 7
                    end = line.find('"', start)
                    csrf_token = line[start:end]
                    break
                # Try single quotes
                elif "value='" in line:
                    start = line.find("value='") + 7
                    end = line.find("'", start)
                    csrf_token = line[start:end]
                    break
        
        if not csrf_token:
            return False
        
        # POST login
        login_data = {
            'email': email,
            'role': role,
            'csrfmiddlewaretoken': csrf_token
        }
        resp = session.post(f"{BASE_URL}/debug/test_login", data=login_data, timeout=10, allow_redirects=False)
        return resp.status_code in [200, 302]
    except Exception as e:
        if DEBUG:
            print(f"Login failed: {e}")
        return False


def execute_student_scenario(user_id: int) -> List[RequestResult]:
    """Execute student dashboard scenario"""
    results = []
    session = requests.Session()
    email = f"loadtest_student_{user_id}@example.edu"
    
    # Login
    start = time.time()
    success = login_as_role(session, "student", email)
    duration = (time.time() - start) * 1000
    results.append(RequestResult(
        url="/debug/test_login (student)",
        duration_ms=duration,
        status_code=200 if success else 500,
        success=success,
        error="" if success else "Login failed"
    ))
    
    if not success:
        return results
    
    # GET dashboard
    start = time.time()
    try:
        resp = session.get(f"{BASE_URL}/dashboard/", timeout=10)
        duration = (time.time() - start) * 1000
        results.append(RequestResult(
            url="/dashboard/",
            duration_ms=duration,
            status_code=resp.status_code,
            success=resp.status_code in [200, 304]
        ))
    except Exception as e:
        duration = (time.time() - start) * 1000
        results.append(RequestResult(
            url="/dashboard/",
            duration_ms=duration,
            status_code=0,
            success=False,
            error=str(e)
        ))
    
    time.sleep(0.5)  # Think time
    
    # GET teams
    start = time.time()
    try:
        resp = session.get(f"{BASE_URL}/assessments/teams", timeout=10)
        duration = (time.time() - start) * 1000
        results.append(RequestResult(
            url="/assessments/teams",
            duration_ms=duration,
            status_code=resp.status_code,
            success=resp.status_code in [200, 304]
        ))
    except Exception as e:
        duration = (time.time() - start) * 1000
        results.append(RequestResult(
            url="/assessments/teams",
            duration_ms=duration,
            status_code=0,
            success=False,
            error=str(e)
        ))
    
    return results


def execute_faculty_scenario(user_id: int) -> List[RequestResult]:
    """Execute faculty dashboard scenario"""
    results = []
    session = requests.Session()
    email = f"loadtest_prof_{user_id}@example.edu"
    
    # Login
    start = time.time()
    success = login_as_role(session, "professor", email)
    duration = (time.time() - start) * 1000
    results.append(RequestResult(
        url="/debug/test_login (professor)",
        duration_ms=duration,
        status_code=200 if success else 500,
        success=success,
        error="" if success else "Login failed"
    ))
    
    if not success:
        return results
    
    # GET course dashboard
    start = time.time()
    try:
        resp = session.get(f"{BASE_URL}/assessments/courses", timeout=10)
        duration = (time.time() - start) * 1000
        results.append(RequestResult(
            url="/assessments/courses",
            duration_ms=duration,
            status_code=resp.status_code,
            success=resp.status_code in [200, 304]
        ))
    except Exception as e:
        duration = (time.time() - start) * 1000
        results.append(RequestResult(
            url="/assessments/courses",
            duration_ms=duration,
            status_code=0,
            success=False,
            error=str(e)
        ))
    
    return results


def run_load_test(num_users: int, scenario_name: str) -> List[RequestResult]:
    """Run load test with specified number of users"""
    print(f"\nRunning {scenario_name} with {num_users} users...")
    print(f"Starting at {time.strftime('%H:%M:%S')}")
    
    all_results = []
    start_time = time.time()
    
    # 90% students, 10% faculty
    num_students = int(num_users * 0.9)
    num_faculty = num_users - num_students
    
    with ThreadPoolExecutor(max_workers=min(num_users, 50)) as executor:
        futures = []
        
        # Submit student scenarios
        for i in range(num_students):
            futures.append(executor.submit(execute_student_scenario, i))
        
        # Submit faculty scenarios
        for i in range(num_faculty):
            futures.append(executor.submit(execute_faculty_scenario, i))
        
        # Collect results
        completed = 0
        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
                completed += 1
                if completed % 10 == 0:
                    print(f"  Completed: {completed}/{num_users} users")
            except Exception as e:
                print(f"  Error in user scenario: {e}")
    
    total_time = time.time() - start_time
    print(f"Finished at {time.strftime('%H:%M:%S')}")
    print(f"Total test duration: {total_time:.2f}s")
    
    return all_results


def analyze_results(results: List[RequestResult], test_name: str):
    """Analyze and print statistics from test results"""
    print(f"\n{'='*70}")
    print(f"RESULTS: {test_name}")
    print(f"{'='*70}")
    
    # Group by URL
    by_url = {}
    for r in results:
        if r.url not in by_url:
            by_url[r.url] = []
        by_url[r.url].append(r)
    
    # Overall stats
    total_requests = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total_requests - successful
    error_rate = (failed / total_requests * 100) if total_requests > 0 else 0
    
    print(f"\nOverall Statistics:")
    print(f"  Total Requests: {total_requests}")
    print(f"  Successful: {successful} ({100-error_rate:.1f}%)")
    print(f"  Failed: {failed} ({error_rate:.1f}%)")
    
    # Per-endpoint stats
    print(f"\nPer-Endpoint Statistics:")
    print(f"{'Endpoint':<40} {'Count':>7} {'Mean':>8} {'p50':>8} {'p95':>8} {'p99':>8} {'Errors':>7}")
    print("-" * 110)
    
    all_durations = []
    for url in sorted(by_url.keys()):
        endpoint_results = by_url[url]
        durations = [r.duration_ms for r in endpoint_results if r.success]
        errors = sum(1 for r in endpoint_results if not r.success)
        
        all_durations.extend(durations)
        
        if durations:
            mean = statistics.mean(durations)
            p50 = statistics.median(durations)
            p95 = statistics.quantiles(durations, n=20)[18] if len(durations) > 1 else durations[0]
            p99 = statistics.quantiles(durations, n=100)[98] if len(durations) > 1 else durations[0]
            
            print(f"{url:<40} {len(endpoint_results):>7} {mean:>7.0f}ms {p50:>7.0f}ms {p95:>7.0f}ms {p99:>7.0f}ms {errors:>7}")
        else:
            print(f"{url:<40} {len(endpoint_results):>7} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>8} {errors:>7}")
    
    # Overall timing
    if all_durations:
        print(f"\nOverall Response Times:")
        print(f"  Mean: {statistics.mean(all_durations):.0f}ms")
        print(f"  Median (p50): {statistics.median(all_durations):.0f}ms")
        print(f"  p95: {statistics.quantiles(all_durations, n=20)[18]:.0f}ms")
        print(f"  p99: {statistics.quantiles(all_durations, n=100)[98]:.0f}ms")
    
    # Show sample errors
    error_results = [r for r in results if not r.success and r.error]
    if error_results:
        print(f"\nSample Errors (showing up to 5):")
        for r in error_results[:5]:
            print(f"  {r.url}: {r.error}")


def main():
    global DEBUG
    
    if "--debug" in sys.argv:
        DEBUG = True
    
    # Check if server is running
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✓ Server is reachable at {BASE_URL}")
    except Exception as e:
        print(f"✗ ERROR: Cannot reach server at {BASE_URL}")
        print(f"  Make sure Django is running: python manage.py runserver")
        sys.exit(1)
    
    # Run tests
    print("\n" + "="*70)
    print("PeerAssess Load Testing")
    print("="*70)
    
    # Test 1: 100 users
    results_100 = run_load_test(100, "100 Users Test")
    analyze_results(results_100, "100 Users")
    
    # Wait between tests
    print("\nWaiting 10 seconds before next test...")
    time.sleep(10)
    
    # Test 2: 1000 users
    results_1000 = run_load_test(1000, "1000 Users Test")
    analyze_results(results_1000, "1000 Users")
    
    print("\n" + "="*70)
    print("Load testing complete!")
    print("="*70)


if __name__ == "__main__":
    main()
