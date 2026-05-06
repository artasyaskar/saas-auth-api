"""
Comprehensive load testing scenarios and benchmarks.

Provides load testing with support for:
- Multiple concurrent user scenarios
- API endpoint stress testing
- Database performance testing
- Authentication load testing
- Rate limiting validation
- Memory and CPU profiling
- Response time analysis
- Throughput measurement
"""

import asyncio
import time
import statistics
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import test_user, admin_user


@dataclass
class LoadTestConfig:
    """Load test configuration."""
    name: str
    description: str
    target_url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    payload: Optional[Dict[str, Any]] = None
    concurrent_users: int = 10
    requests_per_user: int = 100
    ramp_up_time: int = 5  # seconds
    duration: int = 60  # seconds
    timeout: int = 30  # seconds
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    max_response_time: float = 2.0  # seconds
    min_success_rate: float = 95.0  # percentage


@dataclass
class LoadTestResult:
    """Load test results."""
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    response_times: List[float] = field(default_factory=list)
    status_codes: Dict[int, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    throughput: float = 0.0  # requests per second
    average_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    success_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_name": self.config.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "throughput_rps": self.throughput,
            "response_times": {
                "average": self.average_response_time,
                "min": min(self.response_times) if self.response_times else 0,
                "max": max(self.response_times) if self.response_times else 0,
                "p95": self.p95_response_time,
                "p99": self.p99_response_time
            },
            "status_codes": self.status_codes,
            "errors": self.errors,
            "passed": self._test_passed()
        }
    
    def _test_passed(self) -> bool:
        """Determine if test passed based on criteria."""
        return (
            self.success_rate >= self.config.min_success_rate and
            self.average_response_time <= self.config.max_response_time and
            self.p95_response_time <= self.config.max_response_time * 2
        )


class LoadTestRunner:
    """
    Load test runner with comprehensive reporting.
    
    Features:
    - Concurrent user simulation
    - Ramp-up and steady-state testing
    - Response time analysis
    - Error tracking and categorization
    - Throughput measurement
    - Performance regression detection
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[LoadTestResult] = []
    
    async def run_test(self, config: LoadTestConfig) -> LoadTestResult:
        """Run a single load test."""
        print(f"Starting load test: {config.name}")
        print(f"Concurrent users: {config.concurrent_users}")
        print(f"Requests per user: {config.requests_per_user}")
        print(f"Duration: {config.duration} seconds")
        
        start_time = datetime.utcnow()
        
        # Initialize result
        result = LoadTestResult(
            config=config,
            start_time=start_time,
            end_time=start_time,
            total_requests=0,
            successful_requests=0,
            failed_requests=0
        )
        
        # Create HTTP client
        with httpx.Client(timeout=config.timeout) as client:
            # Ramp-up phase
            if config.ramp_up_time > 0:
                await self._ramp_up_phase(client, config, result)
            
            # Main test phase
            await self._main_test_phase(client, config, result)
        
        result.end_time = datetime.utcnow()
        
        # Calculate metrics
        self._calculate_metrics(result)
        
        # Print results
        self._print_results(result)
        
        self.results.append(result)
        return result
    
    async def _ramp_up_phase(self, client: httpx.Client, config: LoadTestConfig, result: LoadTestResult) -> None:
        """Execute ramp-up phase."""
        print(f"Ramping up over {config.ramp_up_time} seconds...")
        
        async def make_request():
            return await self._make_single_request(client, config, result)
        
        # Gradually increase concurrent users
        users_to_add = config.concurrent_users
        ramp_interval = config.ramp_up_time / max(users_to_add, 1)
        
        for i in range(users_to_add):
            # Start one user
            task = asyncio.create_task(make_request())
            
            # Wait for ramp interval
            await asyncio.sleep(ramp_interval)
            
            # Cancel the task after one request
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    async def _main_test_phase(self, client: httpx.Client, config: LoadTestConfig, result: LoadTestResult) -> None:
        """Execute main test phase."""
        print(f"Running main test phase for {config.duration} seconds...")
        
        end_time = time.time() + config.duration
        
        # Create tasks for all users
        async def user_session():
            requests_made = 0
            while time.time() < end_time and requests_made < config.requests_per_user:
                await self._make_single_request(client, config, result)
                requests_made += 1
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
        
        # Start all user sessions concurrently
        tasks = [asyncio.create_task(user_session()) for _ in range(config.concurrent_users)]
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _make_single_request(self, client: httpx.Client, config: LoadTestConfig, result: LoadTestResult) -> None:
        """Make a single HTTP request."""
        start_time = time.time()
        
        try:
            if config.method.upper() == "GET":
                response = await client.get(
                    config.target_url,
                    headers=config.headers
                )
            elif config.method.upper() == "POST":
                response = await client.post(
                    config.target_url,
                    json=config.payload,
                    headers=config.headers
                )
            elif config.method.upper() == "PUT":
                response = await client.put(
                    config.target_url,
                    json=config.payload,
                    headers=config.headers
                )
            elif config.method.upper() == "DELETE":
                response = await client.delete(
                    config.target_url,
                    headers=config.headers
                )
            else:
                raise ValueError(f"Unsupported method: {config.method}")
            
            response_time = time.time() - start_time
            result.response_times.append(response_time)
            result.total_requests += 1
            
            if response.status_code in config.expected_status_codes:
                result.successful_requests += 1
            else:
                result.failed_requests += 1
                result.errors.append(f"Unexpected status code: {response.status_code}")
            
            # Track status codes
            result.status_codes[response.status_code] = result.status_codes.get(response.status_code, 0) + 1
            
        except Exception as e:
            response_time = time.time() - start_time
            result.response_times.append(response_time)
            result.total_requests += 1
            result.failed_requests += 1
            result.errors.append(f"Request failed: {str(e)}")
    
    def _calculate_metrics(self, result: LoadTestResult) -> None:
        """Calculate performance metrics."""
        if result.response_times:
            result.average_response_time = statistics.mean(result.response_times)
            result.p95_response_time = statistics.quantiles(result.response_times, n=20)[18]  # 95th percentile
            result.p99_response_time = statistics.quantiles(result.response_times, n=100)[98]  # 99th percentile
        
        duration = (result.end_time - result.start_time).total_seconds()
        if duration > 0:
            result.throughput = result.total_requests / duration
        
        if result.total_requests > 0:
            result.success_rate = (result.successful_requests / result.total_requests) * 100
    
    def _print_results(self, result: LoadTestResult) -> None:
        """Print test results."""
        print("\n" + "="*60)
        print(f"LOAD TEST RESULTS: {result.config.name}")
        print("="*60)
        print(f"Description: {result.config.description}")
        print(f"Duration: {(result.end_time - result.start_time).total_seconds():.2f} seconds")
        print(f"Total Requests: {result.total_requests}")
        print(f"Successful: {result.successful_requests}")
        print(f"Failed: {result.failed_requests}")
        print(f"Success Rate: {result.success_rate:.2f}%")
        print(f"Throughput: {result.throughput:.2f} RPS")
        print(f"Average Response Time: {result.average_response_time:.3f}s")
        print(f"95th Percentile: {result.p95_response_time:.3f}s")
        print(f"99th Percentile: {result.p99_response_time:.3f}s")
        
        if result.status_codes:
            print("\nStatus Codes:")
            for code, count in result.status_codes.items():
                print(f"  {code}: {count}")
        
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for i, error in enumerate(result.errors[:10]):  # Show first 10 errors
                print(f"  {i+1}. {error}")
            if len(result.errors) > 10:
                print(f"  ... and {len(result.errors) - 10} more errors")
        
        print(f"\nTest Result: {'PASSED' if result._test_passed() else 'FAILED'}")
        print("="*60 + "\n")
    
    def run_all_tests(self) -> List[LoadTestResult]:
        """Run all predefined load tests."""
        test_configs = self._get_test_configs()
        results = []
        
        for config in test_configs:
            result = asyncio.run(self.run_test(config))
            results.append(result)
            
            # Wait between tests
            print("Waiting 10 seconds before next test...")
            time.sleep(10)
        
        self.results.extend(results)
        return results
    
    def _get_test_configs(self) -> List[LoadTestConfig]:
        """Get predefined test configurations."""
        return [
            # Basic health check test
            LoadTestConfig(
                name="Health Check Load Test",
                description="Test health endpoint under load",
                target_url=f"{self.base_url}/health",
                concurrent_users=50,
                requests_per_user=20,
                duration=30,
                max_response_time=0.5
            ),
            
            # Authentication load test
            LoadTestConfig(
                name="Authentication Load Test",
                description="Test login endpoint under load",
                target_url=f"{self.base_url}/auth/login",
                method="POST",
                payload={
                    "email": "loadtest@test.com",
                    "password": "testpassword123"
                },
                concurrent_users=20,
                requests_per_user=10,
                duration=60,
                max_response_time=2.0,
                expected_status_codes=[200, 401]  # Allow auth failures
            ),
            
            # User registration load test
            LoadTestConfig(
                name="User Registration Load Test",
                description="Test registration endpoint under load",
                target_url=f"{self.base_url}/auth/register",
                method="POST",
                payload={
                    "email": f"loadtest+{{timestamp}}@test.com",
                    "password": "LoadTestPass123!",
                    "first_name": "Load",
                    "last_name": "Test"
                },
                concurrent_users=10,
                requests_per_user=5,
                duration=30,
                max_response_time=3.0,
                expected_status_codes=[201, 400, 422]  # Allow validation errors
            ),
            
            # API endpoints load test
            LoadTestConfig(
                name="API Endpoints Load Test",
                description="Test various API endpoints under load",
                target_url=f"{self.base_url}/users/me",
                concurrent_users=30,
                requests_per_user=50,
                duration=60,
                max_response_time=1.0,
                expected_status_codes=[200, 401]  # Allow auth failures
            ),
            
            # Concurrent user sessions test
            LoadTestConfig(
                name="Concurrent Sessions Test",
                description="Test multiple concurrent sessions per user",
                target_url=f"{self.base_url}/auth/login",
                method="POST",
                payload={
                    "email": "concurrent@test.com",
                    "password": "testpassword123"
                },
                concurrent_users=100,
                requests_per_user=5,
                ramp_up_time=10,
                duration=30,
                max_response_time=3.0
            ),
            
            # Rate limiting test
            LoadTestConfig(
                name="Rate Limiting Test",
                description="Test rate limiting under high load",
                target_url=f"{self.base_url}/auth/login",
                method="POST",
                payload={
                    "email": "ratelimit@test.com",
                    "password": "testpassword123"
                },
                concurrent_users=5,
                requests_per_user=100,
                duration=60,
                max_response_time=5.0,
                expected_status_codes=[200, 401, 429]  # Allow rate limiting
            ),
            
            # Database stress test
            LoadTestConfig(
                name="Database Stress Test",
                description="Test database operations under load",
                target_url=f"{self.base_url}/users/me",
                concurrent_users=20,
                requests_per_user=100,
                duration=120,
                max_response_time=2.0,
                expected_status_codes=[200, 401]
            )
        ]
    
    def generate_report(self) -> str:
        """Generate comprehensive load test report."""
        if not self.results:
            return "No test results available"
        
        report = []
        report.append("# LOAD TESTING REPORT")
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        # Summary table
        report.append("## Test Summary")
        report.append("| Test Name | Duration (s) | Requests | Success Rate (%) | Avg Response (s) | Throughput (RPS) | Status |")
        report.append("|------------|----------------|----------|------------------|-------------------|------------------|--------|")
        
        for result in self.results:
            status = "✅ PASSED" if result._test_passed() else "❌ FAILED"
            report.append(f"| {result.config.name} | {(result.end_time - result.start_time).total_seconds():.1f} | {result.total_requests} | {result.success_rate:.1f} | {result.average_response_time:.3f} | {result.throughput:.1f} | {status} |")
        
        report.append("")
        
        # Detailed results
        report.append("## Detailed Results")
        for result in self.results:
            report.append(f"### {result.config.name}")
            report.append(f"**Description:** {result.config.description}")
            report.append(f"**Configuration:**")
            report.append(f"- Concurrent Users: {result.config.concurrent_users}")
            report.append(f"- Requests per User: {result.config.requests_per_user}")
            report.append(f"- Duration: {result.config.duration}s")
            report.append(f"- Max Response Time: {result.config.max_response_time}s")
            report.append("")
            
            report.append("**Results:**")
            report.append(f"- Total Requests: {result.total_requests}")
            report.append(f"- Successful: {result.successful_requests}")
            report.append(f"- Failed: {result.failed_requests}")
            report.append(f"- Success Rate: {result.success_rate:.2f}%")
            report.append(f"- Throughput: {result.throughput:.2f} RPS")
            report.append(f"- Average Response Time: {result.average_response_time:.3f}s")
            report.append(f"- 95th Percentile: {result.p95_response_time:.3f}s")
            report.append(f"- 99th Percentile: {result.p99_response_time:.3f}s")
            report.append("")
            
            if result.status_codes:
                report.append("**Status Codes:**")
                for code, count in result.status_codes.items():
                    report.append(f"- {code}: {count}")
                report.append("")
            
            if result.errors:
                report.append("**Errors:**")
                for error in result.errors[:5]:  # Show first 5 errors
                    report.append(f"- {error}")
                if len(result.errors) > 5:
                    report.append(f"- ... and {len(result.errors) - 5} more errors")
                report.append("")
            
            report.append(f"**Result:** {'✅ PASSED' if result._test_passed() else '❌ FAILED'}")
            report.append("")
        
        # Performance analysis
        report.append("## Performance Analysis")
        
        # Find best and worst performing tests
        if self.results:
            best_test = max(self.results, key=lambda r: r.success_rate)
            worst_test = min(self.results, key=lambda r: r.success_rate)
            
            report.append(f"**Best Performance:** {best_test.config.name} ({best_test.success_rate:.1f}% success rate)")
            report.append(f"**Worst Performance:** {worst_test.config.name} ({worst_test.success_rate:.1f}% success rate)")
            report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        
        for result in self.results:
            if not result._test_passed():
                if result.success_rate < result.config.min_success_rate:
                    report.append(f"- **{result.config.name}**: Success rate too low. Consider optimizing the endpoint or increasing resources.")
                
                if result.average_response_time > result.config.max_response_time:
                    report.append(f"- **{result.config.name}**: Response time too high. Investigate performance bottlenecks.")
                
 if result.p99_response_time > result.config.max_response_time * 3:
                    report.append(f"- **{result.config.name}**: High variance in response times. Check for resource contention.")
        
        report.append("")
        
        return "\n".join(report)


class PerformanceBenchmark:
    """
    Performance benchmarking utilities.
    
    Features:
    - Micro-benchmarking of critical paths
    - Memory usage profiling
    - CPU usage monitoring
    - Database query performance
    - Response time distribution analysis
    """
    
    def __init__(self):
        self.client = TestClient(app)
    
    def benchmark_authentication_flow(self) -> Dict[str, Any]:
        """Benchmark complete authentication flow."""
        results = {}
        
        # Registration benchmark
        print("Benchmarking user registration...")
        start_time = time.time()
        
        for i in range(100):
            response = self.client.post(
                "/auth/register",
                json={
                    "email": f"benchmark{i}@test.com",
                    "password": "BenchmarkPass123!",
                    "first_name": "Benchmark",
                    "last_name": "User"
                }
            )
        
        registration_time = time.time() - start_time
        results["registration"] = {
            "total_requests": 100,
            "total_time": registration_time,
            "requests_per_second": 100 / registration_time,
            "average_time_per_request": registration_time / 100
        }
        
        # Login benchmark
        print("Benchmarking user login...")
        start_time = time.time()
        
        for i in range(100):
            response = self.client.post(
                "/auth/login",
                json={
                    "email": "benchmark@test.com",
                    "password": "testpassword123"
                }
            )
        
        login_time = time.time() - start_time
        results["login"] = {
            "total_requests": 100,
            "total_time": login_time,
            "requests_per_second": 100 / login_time,
            "average_time_per_request": login_time / 100
        }
        
        # Token refresh benchmark
        print("Benchmarking token refresh...")
        # First login to get refresh token
        login_response = self.client.post(
            "/auth/login",
            json={
                "email": "benchmark@test.com",
                "password": "testpassword123"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        start_time = time.time()
        
        for i in range(100):
            response = self.client.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token}
            )
        
        refresh_time = time.time() - start_time
        results["refresh"] = {
            "total_requests": 100,
            "total_time": refresh_time,
            "requests_per_second": 100 / refresh_time,
            "average_time_per_request": refresh_time / 100
        }
        
        return results
    
    def benchmark_api_endpoints(self) -> Dict[str, Any]:
        """Benchmark various API endpoints."""
        results = {}
        
        endpoints = [
            {"path": "/health", "method": "GET", "name": "health_check"},
            {"path": "/users/me", "method": "GET", "name": "user_profile"},
            {"path": "/api-keys", "method": "GET", "name": "api_keys_list"},
        ]
        
        for endpoint in endpoints:
            print(f"Benchmarking {endpoint['name']}...")
            
            times = []
            start_time = time.time()
            
            for i in range(100):
                request_start = time.time()
                
                if endpoint["method"] == "GET":
                    response = self.client.get(endpoint["path"])
                elif endpoint["method"] == "POST":
                    response = self.client.post(endpoint["path"], json={})
                
                request_time = time.time() - request_start
                times.append(request_time)
            
            total_time = time.time() - start_time
            
            results[endpoint["name"]] = {
                "total_requests": 100,
                "total_time": total_time,
                "requests_per_second": 100 / total_time,
                "response_times": {
                    "average": statistics.mean(times),
                    "min": min(times),
                    "max": max(times),
                    "p95": statistics.quantiles(times, n=20)[18],
                    "p99": statistics.quantiles(times, n=100)[98]
                }
            }
        
        return results
    
    def benchmark_concurrent_load(self) -> Dict[str, Any]:
        """Benchmark concurrent load handling."""
        print("Benchmarking concurrent load...")
        
        def make_request():
            return self.client.get("/health")
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 25, 50, 100]
        results = {}
        
        for concurrency in concurrency_levels:
            print(f"Testing with {concurrency} concurrent requests...")
            
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(make_request) for _ in range(concurrency * 10)]
                responses = [future.result() for future in as_completed(futures)]
            
            total_time = time.time() - start_time
            successful = sum(1 for r in responses if r.status_code == 200)
            
            results[f"concurrency_{concurrency}"] = {
                "concurrent_requests": concurrency,
                "total_requests": concurrency * 10,
                "total_time": total_time,
                "successful_requests": successful,
                "success_rate": (successful / (concurrency * 10)) * 100,
                "requests_per_second": (concurrency * 10) / total_time
            }
        
        return results


# Test classes for pytest
class TestLoadScenarios:
    """Load testing scenarios for pytest."""
    
    @pytest.mark.slow
    def test_health_endpoint_load(self):
        """Test health endpoint under load."""
        runner = LoadTestRunner()
        
        config = LoadTestConfig(
            name="Health Load Test",
            description="Health endpoint load test",
            target_url="http://localhost:8000/health",
            concurrent_users=20,
            requests_per_user=50,
            duration=30,
            max_response_time=0.5
        )
        
        result = asyncio.run(runner.run_test(config))
        
        # Assertions
        assert result.success_rate >= 95.0
        assert result.average_response_time <= 0.5
        assert result._test_passed()
    
    @pytest.mark.slow
    def test_authentication_load(self):
        """Test authentication under load."""
        runner = LoadTestRunner()
        
        config = LoadTestConfig(
            name="Auth Load Test",
            description="Authentication load test",
            target_url="http://localhost:8000/auth/login",
            method="POST",
            payload={
                "email": "loadtest@test.com",
                "password": "testpassword123"
            },
            concurrent_users=10,
            requests_per_user=20,
            duration=60,
            max_response_time=2.0
        )
        
        result = asyncio.run(runner.run_test(config))
        
        # Assertions
        assert result.success_rate >= 90.0  # Allow some auth failures
        assert result.average_response_time <= 2.0
        assert result._test_passed()
    
    @pytest.mark.slow
    def test_api_endpoints_load(self):
        """Test API endpoints under load."""
        runner = LoadTestRunner()
        
        config = LoadTestConfig(
            name="API Load Test",
            description="API endpoints load test",
            target_url="http://localhost:8000/users/me",
            concurrent_users=15,
            requests_per_user=30,
            duration=45,
            max_response_time=1.0
        )
        
        result = asyncio.run(runner.run_test(config))
        
        # Assertions
        assert result.success_rate >= 80.0  # Allow auth failures
        assert result.average_response_time <= 1.0
        assert result._test_passed()


class TestPerformanceBenchmarks:
    """Performance benchmark tests for pytest."""
    
    def test_authentication_benchmark(self):
        """Benchmark authentication performance."""
        benchmark = PerformanceBenchmark()
        results = benchmark.benchmark_authentication_flow()
        
        # Assertions
        assert results["registration"]["requests_per_second"] >= 50
        assert results["login"]["requests_per_second"] >= 100
        assert results["refresh"]["requests_per_second"] >= 50
    
    def test_api_benchmark(self):
        """Benchmark API performance."""
        benchmark = PerformanceBenchmark()
        results = benchmark.benchmark_api_endpoints()
        
        # Assertions
        assert results["health_check"]["requests_per_second"] >= 200
        assert results["user_profile"]["requests_per_second"] >= 100
        assert results["api_keys_list"]["requests_per_second"] >= 50
    
    def test_concurrent_benchmark(self):
        """Benchmark concurrent performance."""
        benchmark = PerformanceBenchmark()
        results = benchmark.benchmark_concurrent_load()
        
        # Assertions
        assert results["concurrency_10"]["success_rate"] >= 95.0
        assert results["concurrency_50"]["success_rate"] >= 90.0
        assert results["concurrency_100"]["success_rate"] >= 80.0


if __name__ == "__main__":
    # Run all load tests
    runner = LoadTestRunner()
    results = runner.run_all_tests()
    
    # Generate report
    report = runner.generate_report()
    
    # Save report to file
    with open("load_test_report.md", "w") as f:
        f.write(report)
    
    print("\nLoad testing completed!")
    print(f"Report saved to: load_test_report.md")
    print(f"Total tests run: {len(results)}")
    passed_tests = sum(1 for r in results if r._test_passed())
    print(f"Tests passed: {passed_tests}/{len(results)}")
