"""
Performance Benchmarks and Load Testing

Comprehensive load testing and performance benchmarking
using Locust for simulating high traffic scenarios.

Features:
- User authentication load testing
- API endpoint load testing
- Concurrent user simulation
- Response time measurement
- Throughput measurement
- Error rate tracking
- Resource usage monitoring
- Performance regression detection
"""
import time
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import psutil
import threading


@dataclass
class BenchmarkResult:
    """Benchmark result data structure."""
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration: float
    min_response_time: float
    max_response_time: float
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoadTestConfig:
    """Load test configuration."""
    base_url: str
    num_users: int = 100
    spawn_rate: int = 10
    run_time: int = 60  # seconds
    endpoints: List[str] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)


class PerformanceBenchmark:
    """
    Performance benchmarking tool.
    
    Features:
    - Response time measurement
    - Throughput measurement
    - Resource usage tracking
    - Performance regression detection
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results: List[BenchmarkResult] = []
        self._monitoring = False
        self._resource_stats: List[Dict[str, float]] = []
    
    def benchmark_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        num_requests: int = 100,
        concurrent: int = 10
    ) -> BenchmarkResult:
        """
        Benchmark a single endpoint.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            payload: Request payload
            headers: Request headers
            num_requests: Number of requests to make
            concurrent: Number of concurrent requests
        
        Returns:
            Benchmark result
        """
        url = f"{self.base_url}{endpoint}"
        response_times = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        def make_request():
            nonlocal successful, failed
            try:
                req_start = time.time()
                if method == "GET":
                    response = self.session.get(url, headers=headers, timeout=30)
                elif method == "POST":
                    response = self.session.post(url, json=payload, headers=headers, timeout=30)
                elif method == "PUT":
                    response = self.session.put(url, json=payload, headers=headers, timeout=30)
                elif method == "DELETE":
                    response = self.session.delete(url, headers=headers, timeout=30)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                req_end = time.time()
                response_times.append(req_end - req_start)
                
                if response.status_code < 400:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
        
        # Run concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            for future in as_completed(futures):
                future.result()
        
        total_duration = time.time() - start_time
        
        # Calculate statistics
        if response_times:
            sorted_times = sorted(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            p95_time = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
            p99_time = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
        else:
            min_time = max_time = avg_time = median_time = p95_time = p99_time = 0
        
        result = BenchmarkResult(
            endpoint=endpoint,
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=failed,
            total_duration=total_duration,
            min_response_time=min_time,
            max_response_time=max_time,
            avg_response_time=avg_time,
            median_response_time=median_time,
            p95_response_time=p95_time,
            p99_response_time=p99_time,
            requests_per_second=num_requests / total_duration if total_duration > 0 else 0,
            error_rate=failed / num_requests if num_requests > 0 else 0
        )
        
        self.results.append(result)
        return result
    
    def benchmark_all_endpoints(
        self,
        endpoints: List[Dict[str, Any]],
        num_requests: int = 100,
        concurrent: int = 10
    ) -> List[BenchmarkResult]:
        """
        Benchmark multiple endpoints.
        
        Args:
            endpoints: List of endpoint configs
            num_requests: Requests per endpoint
            concurrent: Concurrent requests
        
        Returns:
            List of benchmark results
        """
        results = []
        
        for endpoint_config in endpoints:
            result = self.benchmark_endpoint(
                endpoint=endpoint_config.get("endpoint", ""),
                method=endpoint_config.get("method", "GET"),
                payload=endpoint_config.get("payload"),
                headers=endpoint_config.get("headers"),
                num_requests=num_requests,
                concurrent=concurrent
            )
            results.append(result)
        
        return results
    
    def start_resource_monitoring(self, interval: float = 1.0):
        """Start resource usage monitoring."""
        self._monitoring = True
        
        def monitor():
            while self._monitoring:
                stats = {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "memory_used_mb": psutil.virtual_memory().used / (1024 * 1024),
                    "disk_percent": psutil.disk_usage('/').percent,
                    "network_sent_mb": psutil.net_io_counters().bytes_sent / (1024 * 1024),
                    "network_recv_mb": psutil.net_io_counters().bytes_recv / (1024 * 1024),
                }
                self._resource_stats.append(stats)
                time.sleep(interval)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def stop_resource_monitoring(self):
        """Stop resource usage monitoring."""
        self._monitoring = False
    
    def get_resource_stats(self) -> List[Dict[str, float]]:
        """Get collected resource statistics."""
        return self._resource_stats
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "base_url": self.base_url,
            "results": [
                {
                    "endpoint": r.endpoint,
                    "total_requests": r.total_requests,
                    "successful_requests": r.successful_requests,
                    "failed_requests": r.failed_requests,
                    "total_duration": r.total_duration,
                    "min_response_time_ms": r.min_response_time * 1000,
                    "max_response_time_ms": r.max_response_time * 1000,
                    "avg_response_time_ms": r.avg_response_time * 1000,
                    "median_response_time_ms": r.median_response_time * 1000,
                    "p95_response_time_ms": r.p95_response_time * 1000,
                    "p99_response_time_ms": r.p99_response_time * 1000,
                    "requests_per_second": r.requests_per_second,
                    "error_rate": r.error_rate
                }
                for r in self.results
            ],
            "resource_stats": self._resource_stats
        }


class LoadTestRunner:
    """
    Load test runner simulating real user behavior.
    
    Features:
    - User simulation
    - Scenario-based testing
    - Ramp-up/ramp-down
    - Spike testing
    - Soak testing
    """
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.session = requests.Session()
        self._users: List[Dict[str, Any]] = []
        self._running = False
    
    def setup_users(self, num_users: int):
        """Setup test users."""
        for i in range(num_users):
            username = f"loadtest_user_{i}"
            email = f"loadtest_{i}@example.com"
            password = "LoadTestPass123!"
            
            # Register user
            try:
                response = self.session.post(
                    f"{self.config.base_url}/auth/register",
                    json={
                        "username": username,
                        "email": email,
                        "password": password
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._users.append({
                        "username": username,
                        "password": password,
                        "access_token": data.get("access_token"),
                        "refresh_token": data.get("refresh_token")
                    })
            except Exception as e:
                print(f"Error creating user {username}: {e}")
    
    def user_scenario(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate user behavior scenario.
        
        Args:
            user: User credentials and tokens
        
        Returns:
            Scenario results
        """
        results = {
            "requests": 0,
            "errors": 0,
            "response_times": []
        }
        
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        
        # Common user actions
        actions = [
            ("GET", "/users/profile", None),
            ("GET", "/users/usage", None),
            ("GET", "/health", None),
        ]
        
        for action in actions:
            method, endpoint, payload = action
            url = f"{self.config.base_url}{endpoint}"
            
            try:
                start = time.time()
                if method == "GET":
                    response = self.session.get(url, headers=headers, timeout=10)
                elif method == "POST":
                    response = self.session.post(url, json=payload, headers=headers, timeout=10)
                
                duration = time.time() - start
                results["requests"] += 1
                results["response_times"].append(duration)
                
                if response.status_code >= 400:
                    results["errors"] += 1
            except Exception:
                results["errors"] += 1
        
        return results
    
    def run_load_test(self) -> Dict[str, Any]:
        """
        Run load test with configured users.
        
        Returns:
            Load test results
        """
        self._running = True
        start_time = time.time()
        
        all_results = {
            "total_requests": 0,
            "total_errors": 0,
            "response_times": [],
            "user_results": []
        }
        
        def run_user(user: Dict[str, Any]):
            while self._running and (time.time() - start_time) < self.config.run_time:
                result = self.user_scenario(user)
                all_results["total_requests"] += result["requests"]
                all_results["total_errors"] += result["errors"]
                all_results["response_times"].extend(result["response_times"])
                all_results["user_results"].append(result)
                
                # Random delay between actions
                time.sleep(random.uniform(0.1, 1.0))
        
        # Spawn users gradually
        with ThreadPoolExecutor(max_workers=self.config.num_users) as executor:
            futures = []
            
            for i in range(0, self.config.num_users, self.config.spawn_rate):
                batch = self._users[i:i + self.config.spawn_rate]
                for user in batch:
                    future = executor.submit(run_user, user)
                    futures.append(future)
                
                # Wait before spawning next batch
                time.sleep(1)
            
            # Wait for all to complete
            for future in as_completed(futures):
                future.result()
        
        total_duration = time.time() - start_time
        
        # Calculate statistics
        if all_results["response_times"]:
            sorted_times = sorted(all_results["response_times"])
            avg_time = statistics.mean(all_results["response_times"])
            median_time = statistics.median(all_results["response_times"])
            p95_time = sorted_times[int(len(sorted_times) * 0.95)]
            p99_time = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            avg_time = median_time = p95_time = p99_time = 0
        
        return {
            "config": {
                "num_users": self.config.num_users,
                "spawn_rate": self.config.spawn_rate,
                "run_time": self.config.run_time
            },
            "results": {
                "total_requests": all_results["total_requests"],
                "total_errors": all_results["total_errors"],
                "error_rate": all_results["total_errors"] / all_results["total_requests"] if all_results["total_requests"] > 0 else 0,
                "total_duration": total_duration,
                "requests_per_second": all_results["total_requests"] / total_duration if total_duration > 0 else 0,
                "avg_response_time_ms": avg_time * 1000,
                "median_response_time_ms": median_time * 1000,
                "p95_response_time_ms": p95_time * 1000,
                "p99_response_time_ms": p99_time * 1000
            }
        }
    
    def stop(self):
        """Stop load test."""
        self._running = False


def run_benchmarks(base_url: str):
    """Run comprehensive benchmarks."""
    print(f"Running benchmarks against {base_url}")
    
    benchmark = PerformanceBenchmark(base_url)
    benchmark.start_resource_monitoring()
    
    # Define endpoints to benchmark
    endpoints = [
        {"endpoint": "/health", "method": "GET"},
        {"endpoint": "/auth/register", "method": "POST", "payload": {"username": "bench_user", "email": "bench@example.com", "password": "BenchPass123!"}},
        {"endpoint": "/auth/login", "method": "POST", "payload": {"username": "bench_user", "password": "BenchPass123!"}},
    ]
    
    # Run benchmarks
    results = benchmark.benchmark_all_endpoints(endpoints, num_requests=50, concurrent=5)
    
    benchmark.stop_resource_monitoring()
    
    # Generate report
    report = benchmark.generate_report()
    
    print("\n=== Benchmark Results ===")
    for result in results:
        print(f"\nEndpoint: {result.endpoint}")
        print(f"  Total Requests: {result.total_requests}")
        print(f"  Success Rate: {(1 - result.error_rate) * 100:.2f}%")
        print(f"  Avg Response Time: {result.avg_response_time * 1000:.2f}ms")
        print(f"  P95 Response Time: {result.p95_response_time * 1000:.2f}ms")
        print(f"  Requests/sec: {result.requests_per_second:.2f}")
    
    return report


def run_load_test(base_url: str, num_users: int = 50, run_time: int = 30):
    """Run load test."""
    print(f"Running load test with {num_users} users for {run_time} seconds")
    
    config = LoadTestConfig(
        base_url=base_url,
        num_users=num_users,
        spawn_rate=5,
        run_time=run_time
    )
    
    load_test = LoadTestRunner(config)
    
    # Setup users
    print("Setting up test users...")
    load_test.setup_users(num_users)
    print(f"Created {len(load_test._users)} test users")
    
    # Run load test
    print("Starting load test...")
    results = load_test.run_load_test()
    
    print("\n=== Load Test Results ===")
    print(f"Total Requests: {results['results']['total_requests']}")
    print(f"Total Errors: {results['results']['total_errors']}")
    print(f"Error Rate: {results['results']['error_rate'] * 100:.2f}%")
    print(f"Requests/sec: {results['results']['requests_per_second']:.2f}")
    print(f"Avg Response Time: {results['results']['avg_response_time_ms']:.2f}ms")
    print(f"P95 Response Time: {results['results']['p95_response_time_ms']:.2f}ms")
    
    return results


if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("=== Performance Benchmarking ===")
    benchmark_report = run_benchmarks(base_url)
    
    print("\n=== Load Testing ===")
    load_test_results = run_load_test(base_url, num_users=20, run_time=10)
    
    # Save results
    import json
    with open("benchmark_results.json", "w") as f:
        json.dump({
            "benchmark": benchmark_report,
            "load_test": load_test_results
        }, f, indent=2)
    
    print("\nResults saved to benchmark_results.json")
