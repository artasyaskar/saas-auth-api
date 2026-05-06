"""
Enterprise-grade dependency injection system.

Provides a comprehensive dependency injection container with support for:
- Service registration and resolution
- Singleton and scoped lifetimes
- Interface-based binding
- Circular dependency detection
- Configuration injection
- Health monitoring
"""

import inspect
import threading
from typing import Any, Dict, List, Type, TypeVar, Callable, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime enumeration."""
    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"


@dataclass
class ServiceDescriptor:
    """Service registration descriptor."""
    interface: Type
    implementation: Type
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    factory: Optional[Callable] = None
    dependencies: List[Type] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DIContainer:
    """
    Enterprise dependency injection container.
    
    Features:
    - Service registration and resolution
    - Lifetime management (singleton, scoped, transient)
    - Circular dependency detection
    - Interface-based binding
    - Configuration injection
    - Health monitoring
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._lock = threading.RLock()
        self._resolution_stack: List[Type] = []
        self._metrics = {
            "registrations": 0,
            "resolutions": 0,
            "singleton_creations": 0,
            "scoped_creations": 0,
            "transient_creations": 0,
            "circular_dependencies_detected": 0
        }
    
    def register(
        self,
        interface: Type[T],
        implementation: Type[T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        factory: Optional[Callable[[], T]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a service implementation.
        
        Args:
            interface: Service interface or base class
            implementation: Service implementation class
            lifetime: Service lifetime
            factory: Optional factory function
            tags: Service tags for grouping
            metadata: Additional metadata
        """
        with self._lock:
            # Validate implementation
            if not issubclass(implementation, interface):
                raise ValueError(f"Implementation {implementation} must implement {interface}")
            
            # Detect dependencies automatically
            dependencies = self._detect_dependencies(implementation)
            
            descriptor = ServiceDescriptor(
                interface=interface,
                implementation=implementation,
                lifetime=lifetime,
                factory=factory,
                dependencies=dependencies,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            self._services[interface] = descriptor
            self._metrics["registrations"] += 1
            
            logger.info(
                f"Registered service: {interface.__name__} -> {implementation.__name__}",
                lifetime=lifetime.value,
                dependencies=[dep.__name__ for dep in dependencies]
            )
    
    def register_singleton(
        self,
        interface: Type[T],
        implementation: Type[T],
        factory: Optional[Callable[[], T]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a singleton service."""
        self.register(interface, implementation, ServiceLifetime.SINGLETON, factory, tags, metadata)
    
    def register_scoped(
        self,
        interface: Type[T],
        implementation: Type[T],
        factory: Optional[Callable[[], T]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a scoped service."""
        self.register(interface, implementation, ServiceLifetime.SCOPED, factory, tags, metadata)
    
    def register_instance(
        self,
        interface: Type[T],
        instance: T,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a pre-created instance as singleton.
        
        Args:
            interface: Service interface
            instance: Pre-created instance
            tags: Service tags
            metadata: Additional metadata
        """
        with self._lock:
            self._instances[interface] = instance
            
            descriptor = ServiceDescriptor(
                interface=interface,
                implementation=type(instance),
                lifetime=ServiceLifetime.SINGLETON,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            self._services[interface] = descriptor
            self._metrics["registrations"] += 1
            
            logger.info(f"Registered instance: {interface.__name__} -> {type(instance).__name__}")
    
    def resolve(self, interface: Type[T], scope: Optional[str] = None) -> T:
        """
        Resolve a service instance.
        
        Args:
            interface: Service interface to resolve
            scope: Optional scope name for scoped services
            
        Returns:
            Service instance
        """
        with self._lock:
            # Check for circular dependencies
            if interface in self._resolution_stack:
                cycle = " -> ".join([cls.__name__ for cls in self._resolution_stack] + [interface.__name__])
                self._metrics["circular_dependencies_detected"] += 1
                raise ValueError(f"Circular dependency detected: {cycle}")
            
            self._resolution_stack.append(interface)
            
            try:
                # Check if service is registered
                if interface not in self._services:
                    raise ValueError(f"Service {interface.__name__} is not registered")
                
                descriptor = self._services[interface]
                
                # Handle different lifetimes
                if descriptor.lifetime == ServiceLifetime.SINGLETON:
                    return self._resolve_singleton(descriptor)
                elif descriptor.lifetime == ServiceLifetime.SCOPED:
                    return self._resolve_scoped(descriptor, scope)
                else:  # TRANSIENT
                    return self._resolve_transient(descriptor)
                    
            finally:
                self._resolution_stack.pop()
    
    def _resolve_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve singleton service."""
        # Check if instance already exists
        if descriptor.interface in self._instances:
            return self._instances[descriptor.interface]
        
        # Create new instance
        instance = self._create_instance(descriptor)
        self._instances[descriptor.interface] = instance
        self._metrics["singleton_creations"] += 1
        
        return instance
    
    def _resolve_scoped(self, descriptor: ServiceDescriptor, scope: Optional[str]) -> Any:
        """Resolve scoped service."""
        if scope is None:
            # Default scope for scoped services without explicit scope
            scope = "default"
        
        # Check if scoped instance exists
        if scope not in self._scoped_instances:
            self._scoped_instances[scope] = {}
        
        if descriptor.interface in self._scoped_instances[scope]:
            return self._scoped_instances[scope][descriptor.interface]
        
        # Create new instance
        instance = self._create_instance(descriptor)
        self._scoped_instances[scope][descriptor.interface] = instance
        self._metrics["scoped_creations"] += 1
        
        return instance
    
    def _resolve_transient(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve transient service (always creates new instance)."""
        instance = self._create_instance(descriptor)
        self._metrics["transient_creations"] += 1
        return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create service instance with dependency injection."""
        # Use factory if provided
        if descriptor.factory:
            return descriptor.factory()
        
        # Resolve dependencies
        dependencies = {}
        for dep_type in descriptor.dependencies:
            dependencies[dep_type] = self.resolve(dep_type)
        
        # Create instance with dependencies
        try:
            # Try constructor injection first
            sig = inspect.signature(descriptor.implementation.__init__)
            param_names = list(sig.parameters.keys())
            
            if param_names:
                # Filter dependencies to match constructor parameters
                constructor_deps = {}
                for param_name, param in sig.parameters.items():
                    if param.annotation != inspect.Parameter.empty:
                        dep_type = param.annotation
                        if dep_type in dependencies:
                            constructor_deps[param_name] = dependencies[dep_type]
                
                instance = descriptor.implementation(**constructor_deps)
            else:
                instance = descriptor.implementation()
            
            # Property injection (for properties that can be set)
            for dep_type, dep_instance in dependencies.items():
                if hasattr(instance, f"_{dep_type.__name__.lower()}"):
                    setattr(instance, f"_{dep_type.__name__.lower()}", dep_instance)
            
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create instance of {descriptor.implementation.__name__}: {str(e)}")
            raise
    
    def _detect_dependencies(self, implementation: Type) -> List[Type]:
        """Detect constructor dependencies using type hints."""
        try:
            sig = inspect.signature(implementation.__init__)
            dependencies = []
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                if param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)
            
            return dependencies
            
        except Exception:
            return []
    
    def is_registered(self, interface: Type) -> bool:
        """Check if a service is registered."""
        return interface in self._services
    
    def get_services_by_tag(self, tag: str) -> List[ServiceDescriptor]:
        """Get all services with a specific tag."""
        return [desc for desc in self._services.values() if tag in desc.tags]
    
    def clear_scope(self, scope: str) -> None:
        """Clear all scoped instances for a specific scope."""
        with self._lock:
            if scope in self._scoped_instances:
                del self._scoped_instances[scope]
                logger.info(f"Cleared scope: {scope}")
    
    def clear_all_scopes(self) -> None:
        """Clear all scoped instances."""
        with self._lock:
            self._scoped_instances.clear()
            logger.info("Cleared all scopes")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get container metrics."""
        with self._lock:
            return {
                **self._metrics,
                "registered_services": len(self._services),
                "singleton_instances": len(self._instances),
                "active_scopes": len(self._scoped_instances),
                "services_by_lifetime": {
                    lifetime.value: len([
                        desc for desc in self._services.values()
                        if desc.lifetime == lifetime
                    ])
                    for lifetime in ServiceLifetime
                }
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform container health check."""
        try:
            # Test resolution of a few key services
            test_results = {}
            
            for interface, descriptor in list(self._services.items())[:5]:  # Test first 5 services
                try:
                    instance = self.resolve(interface)
                    test_results[interface.__name__] = {
                        "status": "healthy",
                        "instance_type": type(instance).__name__
                    }
                except Exception as e:
                    test_results[interface.__name__] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            all_healthy = all(result["status"] == "healthy" for result in test_results.values())
            
            return {
                "healthy": all_healthy,
                "test_results": test_results,
                "metrics": self.get_metrics()
            }
            
        except Exception as e:
            logger.error(f"Container health check failed: {str(e)}")
            return {
                "healthy": False,
                "error": str(e),
                "metrics": self.get_metrics()
            }


class ServiceRegistry:
    """
    Service registry for automatic service discovery and registration.
    
    Features:
    - Automatic service discovery
    - Convention-based registration
    - Module scanning
    - Configuration-based registration
    """
    
    def __init__(self, container: DIContainer):
        self.container = container
        self._registered_modules = set()
    
    def register_from_module(self, module, lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> None:
        """
        Register services from a module using conventions.
        
        Convention: Classes ending with 'Service' are auto-registered
        """
        if module in self._registered_modules:
            return
        
        for name in dir(module):
            obj = getattr(module, name)
            
            # Check if it's a class and ends with 'Service'
            if (inspect.isclass(obj) and 
                name.endswith('Service') and 
                not name.startswith('_')):
                
                # Determine interface (base class)
                bases = [base for base in obj.__bases__ if base != object]
                if bases:
                    interface = bases[0]  # Use first base class as interface
                    self.container.register(interface, obj, lifetime)
                    logger.info(f"Auto-registered service: {name}")
        
        self._registered_modules.add(module)
    
    def register_by_convention(self, package_path: str) -> None:
        """
        Register services by scanning package for conventions.
        
        Args:
            package_path: Python package path to scan
        """
        try:
            import importlib
            import pkgutil
            
            package = importlib.import_module(package_path)
            
            for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
                if not ispkg:
                    module = importlib.import_module(modname)
                    self.register_from_module(module)
                    
        except Exception as e:
            logger.error(f"Failed to register services from {package_path}: {str(e)}")
    
    def register_configuration_services(self, config_dict: Dict[str, Any]) -> None:
        """
        Register services based on configuration.
        
        Args:
            config_dict: Configuration dictionary with service mappings
        """
        for service_name, service_config in config_dict.items():
            try:
                if isinstance(service_config, dict):
                    interface_name = service_config.get('interface')
                    implementation_name = service_config.get('implementation')
                    lifetime_str = service_config.get('lifetime', 'transient')
                    
                    if interface_name and implementation_name:
                        # Dynamic import
                        interface = self._import_class(interface_name)
                        implementation = self._import_class(implementation_name)
                        lifetime = ServiceLifetime(lifetime_str)
                        
                        self.container.register(interface, implementation, lifetime)
                        
            except Exception as e:
                logger.error(f"Failed to register service {service_name}: {str(e)}")
    
    def _import_class(self, class_path: str) -> Type:
        """Import class from string path."""
        module_path, class_name = class_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)


# Global container instance
container = DIContainer()
registry = ServiceRegistry(container)


# Decorators for easy registration
def injectable(
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    tags: Optional[List[str]] = None
):
    """
    Decorator to mark a class as injectable.
    
    Usage:
        @injectable(ServiceLifetime.SINGLETON, tags=["database"])
        class UserService:
            def __init__(self, db_service: DatabaseService):
                self.db_service = db_service
    """
    def decorator(cls):
        # Auto-register the class
        # Determine interface (use base class or the class itself)
        bases = [base for base in cls.__bases__ if base != object]
        interface = bases[0] if bases else cls
        
        container.register(interface, cls, lifetime, tags=tags)
        return cls
    
    return decorator


def singleton(tags: Optional[List[str]] = None):
    """Decorator to mark a class as singleton."""
    return injectable(ServiceLifetime.SINGLETON, tags)


def scoped(tags: Optional[List[str]] = None):
    """Decorator to mark a class as scoped."""
    return injectable(ServiceLifetime.SCOPED, tags)


def inject(interface: Type[T]) -> T:
    """
    Function to inject a dependency.
    
    Usage:
        def user_service(user_repo: DatabaseService = inject(DatabaseService)):
            return user_repo
    """
    return container.resolve(interface)


# Convenience functions
def register_service(
    interface: Type[T],
    implementation: Type[T],
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
) -> None:
    """Register a service."""
    container.register(interface, implementation, lifetime)


def resolve_service(interface: Type[T], scope: Optional[str] = None) -> T:
    """Resolve a service."""
    return container.resolve(interface, scope)


def get_container_metrics() -> Dict[str, Any]:
    """Get container metrics."""
    return container.get_metrics()


def container_health_check() -> Dict[str, Any]:
    """Perform container health check."""
    return container.health_check()


# Context manager for scoped resolution
@contextmanager
def service_scope(scope_name: str = "default"):
    """
    Context manager for scoped service resolution.
    
    Usage:
        with service_scope("request") as scope:
            user_service = resolve_service(UserService, scope)
            # All scoped services will be shared within this scope
    """
    try:
        yield scope_name
    finally:
        container.clear_scope(scope_name)


# Auto-registration helper
def auto_register_services(package_path: str) -> None:
    """Auto-register services from package."""
    registry.register_by_convention(package_path)
