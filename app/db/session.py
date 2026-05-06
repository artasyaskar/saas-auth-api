"""
Enhanced database session management with optimized connection pooling.

Provides enterprise-grade database connection management with support for:
- Connection pooling optimization
- Health checks and monitoring
- Connection retry logic
- Performance metrics
- Connection timeouts
- Read/write splitting support
"""

import time
import threading
from typing import Optional, Dict, Any, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
import structlog

from app.core.config import settings
from app.db.models import Base

logger = structlog.get_logger()


class DatabaseConnectionPool:
    """
    Enhanced database connection pool with monitoring and optimization.
    
    Features:
    - Connection health monitoring
    - Performance metrics
    - Automatic connection recovery
    - Pool size optimization
    - Connection timeout management
    """
    
    def __init__(self, database_url: str, pool_config: Dict[str, Any]):
        self.database_url = database_url
        self.pool_config = pool_config
        self.engine = None
        self.session_factory = None
        self.metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "connection_errors": 0,
            "connection_timeouts": 0,
            "total_queries": 0,
            "slow_queries": 0,
            "average_query_time": 0.0,
            "pool_hits": 0,
            "pool_misses": 0
        }
        self._lock = threading.Lock()
        self._setup_engine()
    
    def _setup_engine(self) -> None:
        """Setup database engine with optimized connection pooling."""
        engine_kwargs = {
            "pool_pre_ping": True,
            "pool_recycle": 3600,  # Recycle connections every hour
            "pool_timeout": 30,   # Timeout for getting connection from pool
        }
        
        if self.database_url.startswith("sqlite"):
            engine_kwargs.update({
                "connect_args": {"check_same_thread": False, "timeout": 20},
                "poolclass": pool.StaticPool,
                "pool_size": 1,
                "max_overflow": 0
            })
        else:
            # PostgreSQL/MySQL optimized settings
            engine_kwargs.update({
                "pool_size": self.pool_config.get("pool_size", 20),
                "max_overflow": self.pool_config.get("max_overflow", 30),
                "pool_timeout": self.pool_config.get("pool_timeout", 30),
                "pool_recycle": self.pool_config.get("pool_recycle", 3600),
                "pool_pre_ping": True,
                "echo": self.pool_config.get("echo", False),
                "connect_args": {
                    "connect_timeout": 10,
                    "application_name": "saas-auth-api",
                    "server_settings": {
                        "jit": "off",  # Disable JIT for better query planning
                        "timezone": "UTC"
                    }
                }
            })
        
        self.engine = create_engine(self.database_url, **engine_kwargs)
        self.session_factory = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine,
            expire_on_commit=False
        )
        
        # Setup event listeners for monitoring
        self._setup_event_listeners()
        
        logger.info("Database connection pool initialized", **self.pool_config)
    
    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for monitoring."""
        
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            """Called when a connection is established."""
            with self._lock:
                self.metrics["total_connections"] += 1
            logger.debug("Database connection established")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Called when a connection is checked out from pool."""
            with self._lock:
                self.metrics["active_connections"] += 1
                self.metrics["pool_hits"] += 1
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Called when a connection is returned to pool."""
            with self._lock:
                self.metrics["active_connections"] = max(0, self.metrics["active_connections"] - 1)
                self.metrics["idle_connections"] += 1
        
        @event.listens_for(self.engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, connection_proxy):
            """Called when a connection is invalidated."""
            with self._lock:
                self.metrics["connection_errors"] += 1
            logger.warning("Database connection invalidated")
        
        @event.listens_for(self.engine, "engine_connect")
        def receive_engine_connect(connection, branch):
            """Called when engine connects to database."""
            if connection:
                # Set connection parameters
                if hasattr(connection, 'connection'):
                    conn = connection.connection
                    if hasattr(conn, 'autocommit'):
                        conn.autocommit = False
        
        @event.listens_for(Session, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Called before SQL execution."""
            context._query_start_time = time.time()
        
        @event.listens_for(Session, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Called after SQL execution."""
            if hasattr(context, '_query_start_time'):
                query_time = time.time() - context._query_start_time
                
                with self._lock:
                    self.metrics["total_queries"] += 1
                    
                    # Update average query time
                    total_queries = self.metrics["total_queries"]
                    current_avg = self.metrics["average_query_time"]
                    self.metrics["average_query_time"] = (
                        (current_avg * (total_queries - 1) + query_time) / total_queries
                    )
                    
                    # Track slow queries (over 1 second)
                    if query_time > 1.0:
                        self.metrics["slow_queries"] += 1
                        logger.warning(
                            "Slow query detected",
                            query_time=query_time,
                            statement=statement[:200] + "..." if len(statement) > 200 else statement
                        )
    
    def get_session(self) -> Session:
        """Get a database session with retry logic."""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                session = self.session_factory()
                
                # Configure session for optimal performance
                session.execute("SET statement_timeout = '30s'")  # 30 second query timeout
                
                return session
                
            except (SQLAlchemyError, DisconnectionError) as e:
                with self._lock:
                    self.metrics["connection_errors"] += 1
                
                if attempt == max_retries - 1:
                    logger.error("Failed to create database session after retries", error=str(e))
                    raise
                
                logger.warning(f"Database connection attempt {attempt + 1} failed, retrying...", error=str(e))
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
        
        raise SQLAlchemyError("Failed to create database session")
    
    @contextmanager
    def get_session_context(self) -> Generator[Session, None, None]:
        """Get a database session context manager."""
        session = None
        try:
            session = self.get_session()
            yield session
            session.commit()
        except Exception as e:
            if session:
                session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            if session:
                session.close()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        try:
            with self.get_session_context() as session:
                # Simple health check query
                result = session.execute("SELECT 1 as health_check")
                health_status = result.fetchone()[0] == 1
                
                # Get pool status
                pool = self.engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
                
                return {
                    "healthy": health_status,
                    "pool_status": pool_status,
                    "metrics": self.get_metrics()
                }
                
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "healthy": False,
                "error": str(e),
                "metrics": self.get_metrics()
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection pool metrics."""
        with self._lock:
            metrics = self.metrics.copy()
        
        # Add current pool status
        if self.engine and self.engine.pool:
            pool = self.engine.pool
            metrics.update({
                "pool_size": pool.size(),
                "pool_checked_in": pool.checkedin(),
                "pool_checked_out": pool.checkedout(),
                "pool_overflow": pool.overflow(),
                "pool_invalid": pool.invalid()
            })
        
        return metrics
    
    def close(self) -> None:
        """Close all database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection pool closed")


# Initialize connection pool
_db_url = settings.database_url
_pool_config = {
    "pool_size": settings.database.pool_size,
    "max_overflow": settings.database.max_overflow,
    "pool_timeout": getattr(settings.database, 'pool_timeout', 30),
    "pool_recycle": getattr(settings.database, 'pool_recycle', 3600),
    "echo": settings.database.echo
}

# Create connection pool instance
connection_pool = DatabaseConnectionPool(_db_url, _pool_config)

# Export engine and session factory for backward compatibility
engine = connection_pool.engine
SessionLocal = connection_pool.session_factory


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Enhanced with connection pooling optimization and error handling.
    """
    session = connection_pool.get_session()
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error("Database session error in get_db", error=str(e))
        raise
    finally:
        session.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Provides automatic commit/rollback and connection cleanup.
    """
    with connection_pool.get_session_context() as session:
        yield session


def get_database_health() -> Dict[str, Any]:
    """Get database health status."""
    return connection_pool.health_check()


def get_database_metrics() -> Dict[str, Any]:
    """Get database performance metrics."""
    return connection_pool.get_metrics()


# Initialize database tables
def create_tables() -> None:
    """Create all database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


# Cleanup function for graceful shutdown
def cleanup_database_connections() -> None:
    """Cleanup database connections on shutdown."""
    connection_pool.close()
