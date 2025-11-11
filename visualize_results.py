#!/usr/bin/env python3
"""
Visualize load test results
"""
import json

# Test results data
results = {
    "100_users": {
        "total_requests": 290,
        "successful": 200,
        "failed": 90,
        "duration_s": 2.75,
        "response_times": {
            "mean_ms": 324,
            "p50_ms": 104,
            "p95_ms": 1304,
            "p99_ms": 2096
        },
        "endpoints": {
            "/debug/test_login (student)": {"count": 90, "mean_ms": 587, "errors": 0},
            "/debug/test_login (professor)": {"count": 10, "mean_ms": 322, "errors": 0},
            "/dashboard/": {"count": 90, "mean_ms": 91, "errors": 0},
            "/assessments/courses": {"count": 10, "mean_ms": 56, "errors": 0},
            "/assessments/teams": {"count": 90, "mean_ms": 0, "errors": 90}
        }
    },
    "1000_users": {
        "total_requests": 2900,
        "successful": 2000,
        "failed": 900,
        "duration_s": 26.30,
        "response_times": {
            "mean_ms": 404,
            "p50_ms": 138,
            "p95_ms": 1676,
            "p99_ms": 3122
        },
        "endpoints": {
            "/debug/test_login (student)": {"count": 900, "mean_ms": 647, "errors": 0},
            "/debug/test_login (professor)": {"count": 100, "mean_ms": 744, "errors": 0},
            "/dashboard/": {"count": 900, "mean_ms": 146, "errors": 0},
            "/assessments/courses": {"count": 100, "mean_ms": 201, "errors": 0},
            "/assessments/teams": {"count": 900, "mean_ms": 0, "errors": 900}
        }
    }
}

def print_ascii_bar(value, max_value, width=40, label=""):
    """Print an ASCII bar chart"""
    filled = int((value / max_value) * width)
    bar = "█" * filled + "░" * (width - filled)
    print(f"{label:<30} {bar} {value:.0f}ms")

def print_results():
    print("\n" + "="*70)
    print("LOAD TEST RESULTS VISUALIZATION")
    print("="*70)
    
    for test_name, data in results.items():
        users = test_name.replace("_", " ").title()
        print(f"\n{users}")
        print("-" * 70)
        
        # Overall stats
        success_rate = (data["successful"] / data["total_requests"]) * 100
        error_rate = (data["failed"] / data["total_requests"]) * 100
        rps = data["total_requests"] / data["duration_s"]
        
        print(f"Total Requests:  {data['total_requests']}")
        print(f"Successful:      {data['successful']} ({success_rate:.1f}%)")
        print(f"Failed:          {data['failed']} ({error_rate:.1f}%)")
        print(f"Duration:        {data['duration_s']:.2f}s")
        print(f"Throughput:      {rps:.1f} req/s")
        
        # Response time bars
        print(f"\nResponse Times:")
        max_time = data["response_times"]["p99_ms"]
        print_ascii_bar(data["response_times"]["mean_ms"], max_time, label="Mean")
        print_ascii_bar(data["response_times"]["p50_ms"], max_time, label="Median (p50)")
        print_ascii_bar(data["response_times"]["p95_ms"], max_time, label="p95")
        print_ascii_bar(data["response_times"]["p99_ms"], max_time, label="p99")
        
        # Endpoint performance
        print(f"\nEndpoint Performance (Mean Response Time):")
        endpoints = [(k, v["mean_ms"]) for k, v in data["endpoints"].items() if v["mean_ms"] > 0]
        if endpoints:
            max_endpoint_time = max(t for _, t in endpoints)
            for endpoint, mean_time in sorted(endpoints, key=lambda x: x[1], reverse=True):
                print_ascii_bar(mean_time, max_endpoint_time, width=30, label=endpoint[:28])
        
        # Error summary
        error_endpoints = [(k, v["errors"]) for k, v in data["endpoints"].items() if v["errors"] > 0]
        if error_endpoints:
            print(f"\n⚠️  ERRORS DETECTED:")
            for endpoint, errors in error_endpoints:
                print(f"   • {endpoint}: {errors} failures ({errors/data['total_requests']*100:.1f}%)")
    
    print("\n" + "="*70)
    print("COMPARISON: 100 vs 1,000 Users")
    print("="*70)
    
    # Calculate degradation
    r100 = results["100_users"]["response_times"]
    r1000 = results["1000_users"]["response_times"]
    
    print(f"\nResponse Time Degradation:")
    print(f"Mean:   {r100['mean_ms']:.0f}ms → {r1000['mean_ms']:.0f}ms  (+{(r1000['mean_ms']/r100['mean_ms']-1)*100:.0f}%)")
    print(f"p50:    {r100['p50_ms']:.0f}ms → {r1000['p50_ms']:.0f}ms  (+{(r1000['p50_ms']/r100['p50_ms']-1)*100:.0f}%)")
    print(f"p95:    {r100['p95_ms']:.0f}ms → {r1000['p95_ms']:.0f}ms  (+{(r1000['p95_ms']/r100['p95_ms']-1)*100:.0f}%)")
    print(f"p99:    {r100['p99_ms']:.0f}ms → {r1000['p99_ms']:.0f}ms  (+{(r1000['p99_ms']/r100['p99_ms']-1)*100:.0f}%)")
    
    print(f"\n{'='*70}")
    print("VERDICT")
    print("="*70)
    print("❌ NOT PRODUCTION READY")
    print("   • 31% error rate (authentication issue)")
    print("   • High latency at p95/p99 under load")
    print("   • SQLite + dev server unsuitable for production")
    print("\n✅ FIXABLE WITH RECOMMENDED IMPROVEMENTS")
    print("   • Migrate to PostgreSQL + Gunicorn")
    print("   • Fix authentication/session handling")
    print("   • Add caching and query optimization")
    print("   • Estimated capacity after fixes: 3,000-5,000 users")
    print("="*70 + "\n")

if __name__ == "__main__":
    print_results()
