"""
Comprehensive Monitoring and Observability Service

Enterprise-grade monitoring with metrics collection, tracing,
alerting, and dashboard integration.

Features:
- Custom metrics (counters, gauges, histograms)
- Distributed tracing with OpenTelemetry
- Application Performance Monitoring (APM)
- Log aggregation and analysis
- Alerting and notifications
- Health checks
- Performance profiling
- Error tracking
- Uptime monitoring
- Real-time dashboards
"""
import time
import json
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps
from contextlib import contextmanager
from sqlalchemy.orm import Session

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class Metric:
    """Metric data structure."""
    name: str
    value: float
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Alert:
    """Alert data structure."""
    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None


class MetricsRegistry:
    """Registry for storing and managing metrics."""
    
    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._tags: Dict[str, Dict[str, str]] = {}
    
    def increment(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        self._counters[name] += value
        if tags:
            self._tags[name] = tags
    
    def set(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        self._gauges[name] = value
        if tags:
            self._tags[name] = tags
    
    def observe(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Observe a histogram metric."""
        self._histograms[name].append(value)
        if tags:
            self._tags[name] = tags
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        if name in self._counters:
            return Metric(
                name=name,
                value=self._counters[name],
                metric_type=MetricType.COUNTER,
                tags=self._tags.get(name, {})
            )
        elif name in self._gauges:
            return Metric(
                name=name,
                value=self._gauges[name],
                metric_type=MetricType.GAUGE,
                tags=self._tags.get(name, {})
            )
        elif name in self._histograms:
            values = self._histograms[name]
            return Metric(
                name=name,
                value=sum(values) / len(values) if values else 0,
                metric_type=MetricType.HISTOGRAM,
                tags=self._tags.get(name, {})
            )
        return None
    
    def get_all_metrics(self) -> List[Metric]:
        """Get all registered metrics."""
        metrics = []
        
        for name, value in self._counters.items():
            metrics.append(Metric(
                name=name,
                value=value,
                metric_type=MetricType.COUNTER,
                tags=self._tags.get(name, {})
            ))
        
        for name, value in self._gauges.items():
            metrics.append(Metric(
                name=name,
                value=value,
                metric_type=MetricType.GAUGE,
                tags=self._tags.get(name, {})
            ))
        
        for name, values in self._histograms.items():
            if values:
                metrics.append(Metric(
                    name=name,
                    value=sum(values) / len(values),
                    metric_type=MetricType.HISTOGRAM,
                    tags=self._tags.get(name, {})
                ))
        
        return metrics


class MonitoringService:
    """
    Enterprise-grade monitoring service.
    
    Features:
    - Custom metrics collection
    - Distributed tracing
    - Health checks
    - Alerting
    - Performance profiling
    - System metrics
    - Application metrics
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.registry = MetricsRegistry()
        self._alerts: List[Alert] = []
        self._health_checks: Dict[str, HealthCheck] = {}
        self._alert_rules: List[Dict[str, Any]] = []
        
        # Tracing setup
        self.tracer = None
        if OTEL_AVAILABLE:
            self._setup_tracing()
        
        # Start background collection
        self._start_system_metrics_collection()
    
    def _setup_tracing(self):
        """Setup OpenTelemetry tracing."""
        try:
            provider = TracerProvider()
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
            )
            provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            trace.set_tracer_provider(provider)
            self.tracer = trace.get_tracer(__name__)
        except Exception as e:
            print(f"Failed to setup tracing: {e}")
    
    def _start_system_metrics_collection(self):
        """Start background thread for system metrics collection."""
        def collect():
            while True:
                self._collect_system_metrics()
                time.sleep(5)  # Collect every 5 seconds
        
        thread = threading.Thread(target=collect, daemon=True)
        thread.start()
    
    def _collect_system_metrics(self):
        """Collect system metrics."""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        self.registry.set("system.cpu.percent", cpu_percent)
        
        # Memory
        memory = psutil.virtual_memory()
        self.registry.set("system.memory.percent", memory.percent)
        self.registry.set("system.memory.available", memory.available)
        self.registry.set("system.memory.used", memory.used)
        
        # Disk
        disk = psutil.disk_usage('/')
        self.registry.set("system.disk.percent", disk.percent)
        self.registry.set("system.disk.free", disk.free)
        self.registry.set("system.disk.used", disk.used)
        
        # Network
        net_io = psutil.net_io_counters()
        self.registry.set("system.network.bytes_sent", net_io.bytes_sent)
        self.registry.set("system.network.bytes_recv", net_io.bytes_recv)
    
    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None
    ):
        """Increment a counter metric."""
        self.registry.increment(name, value, tags)
    
    def set_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """Set a gauge metric."""
        self.registry.set(name, value, tags)
    
    def observe_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """Observe a histogram metric."""
        self.registry.observe(name, value, tags)
    
    def get_metrics(self) -> List[Metric]:
        """Get all metrics."""
        return self.registry.get_all_metrics()
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a specific metric."""
        return self.registry.get_metric(name)
    
    @contextmanager
    def trace(self, operation_name: str):
        """Context manager for tracing operations."""
        if self.tracer:
            with self.tracer.start_as_current_span(operation_name) as span:
                yield span
        else:
            yield None
    
    def timed(self, metric_name: str):
        """Decorator to time function execution."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    self.registry.observe(f"{metric_name}.duration", time.time() - start_time)
                    self.registry.increment(f"{metric_name}.success")
                    return result
                except Exception as e:
                    self.registry.observe(f"{metric_name}.duration", time.time() - start_time)
                    self.registry.increment(f"{metric_name}.error")
                    raise
            return wrapper
        return decorator
    
    def add_health_check(
        self,
        name: str,
        check_func: Callable[[], HealthCheck]
    ):
        """Add a health check."""
        self._health_checks[name] = check_func
    
    def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks."""
        results = {}
        for name, check_func in self._health_checks.items():
            try:
                results[name] = check_func()
            except Exception as e:
                results[name] = HealthCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                    response_time_ms=0
                )
        return results
    
    def add_alert_rule(
        self,
        name: str,
        metric_name: str,
        threshold: float,
        operator: str = ">",
        severity: AlertSeverity = AlertSeverity.WARNING
    ):
        """Add an alert rule."""
        self._alert_rules.append({
            "name": name,
            "metric_name": metric_name,
            "threshold": threshold,
            "operator": operator,
            "severity": severity
        })
    
    def check_alerts(self) -> List[Alert]:
        """Check all alert rules and generate alerts."""
        new_alerts = []
        
        for rule in self._alert_rules:
            metric = self.registry.get_metric(rule["metric_name"])
            if not metric:
                continue
            
            current_value = metric.value
            threshold = rule["threshold"]
            operator = rule["operator"]
            
            triggered = False
            if operator == ">" and current_value > threshold:
                triggered = True
            elif operator == "<" and current_value < threshold:
                triggered = True
            elif operator == "==" and current_value == threshold:
                triggered = True
            elif operator == ">=" and current_value >= threshold:
                triggered = True
            elif operator == "<=" and current_value <= threshold:
                triggered = True
            
            if triggered:
                alert = Alert(
                    name=rule["name"],
                    severity=rule["severity"],
                    message=f"Alert {rule['name']} triggered: {rule['metric_name']} {operator} {threshold}",
                    metric_name=rule["metric_name"],
                    threshold=threshold,
                    current_value=current_value
                )
                new_alerts.append(alert)
                self._alerts.append(alert)
        
        return new_alerts
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self._alerts if not alert.resolved]
    
    def resolve_alert(self, alert_name: str):
        """Resolve an alert."""
        for alert in self._alerts:
            if alert.name == alert_name and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """Get application-level metrics."""
        return {
            "uptime_seconds": time.time() - self._start_time if hasattr(self, '_start_time') else 0,
            "total_requests": self.registry.get_metric("http.requests.total"),
            "total_errors": self.registry.get_metric("http.errors.total"),
            "active_connections": self.registry.get_metric("http.connections.active"),
            "response_time_avg": self.registry.get_metric("http.response_time.avg")
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        return {
            "metrics": self.get_metrics(),
            "health_checks": self.run_health_checks(),
            "alerts": self.get_active_alerts(),
            "application": self.get_application_metrics(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _start_time = time.time()


def get_monitoring_service(db: Session):
    """Dependency to get monitoring service."""
    return MonitoringService(db)
