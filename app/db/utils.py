"""
Database utilities and helper functions.

Provides common database operations, connection management,
and utility functions for database interactions.
"""

from typing import Optional, Dict, Any, List, Type, TypeVar, Generic
from contextlib import contextmanager
from sqlalchemy import text, inspect, func
from sqlalchemy.orm import Session, Query
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
import logging
from datetime import datetime, timedelta

from app.core.exceptions import DatabaseError, ValidationError
from app.db.session import engine, SessionLocal

logger = logging.getLogger(__name__)

# Generic type for model classes
ModelType = TypeVar("ModelType", bound=declarative_base())


class DatabaseUtils:
    """
    Utility class for common database operations.
    
    Provides static methods for database operations like
    connection management, query building, and error handling.
    """
    
    @staticmethod
    @contextmanager
    def get_db_session() -> Session:
        """
        Get a database session with automatic cleanup.
        
        Yields:
            Session: Database session
            
        Raises:
            DatabaseError: If database connection fails
        """
        session = SessionLocal()
        try:
            yield session
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
        finally:
            session.close()
    
    @staticmethod
    @contextmanager
    def get_transaction() -> Session:
        """
        Get a database session with transaction management.
        
        Yields:
            Session: Database session with transaction
            
        Raises:
            DatabaseError: If transaction fails
        """
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database transaction error: {str(e)}")
            raise DatabaseError(f"Database transaction failed: {str(e)}")
        finally:
            session.close()
    
    @staticmethod
    def execute_raw_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query safely.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with DatabaseUtils.get_db_session() as session:
                result = session.execute(text(query), params or {})
                return [dict(row._mapping) for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Raw query execution error: {str(e)}")
            raise DatabaseError(f"Query execution failed: {str(e)}", operation="execute_raw_query")
    
    @staticmethod
    def check_table_exists(table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            inspector = inspect(engine)
            return table_name in inspector.get_table_names()
        except SQLAlchemyError as e:
            logger.error(f"Table existence check error: {str(e)}")
            return False
    
    @staticmethod
    def get_table_info(table_name: str) -> Dict[str, Any]:
        """
        Get information about a database table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
        """
        try:
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            return {
                "table_name": table_name,
                "columns": columns,
                "indexes": indexes,
                "foreign_keys": foreign_keys,
                "column_count": len(columns),
                "index_count": len(indexes),
                "foreign_key_count": len(foreign_keys)
            }
        except SQLAlchemyError as e:
            logger.error(f"Table info retrieval error: {str(e)}")
            raise DatabaseError(f"Failed to get table info: {str(e)}", operation="get_table_info")
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """
        Get database statistics and health information.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with DatabaseUtils.get_db_session() as session:
                # Get connection pool stats
                pool = engine.pool
                
                # Get table counts
                inspector = inspect(engine)
                table_names = inspector.get_table_names()
                
                # Get database size (PostgreSQL specific)
                db_size_query = "SELECT pg_size_pretty(pg_database_size(current_database())) as size"
                try:
                    size_result = session.execute(text(db_size_query))
                    db_size = size_result.scalar()
                except SQLAlchemyError:
                    db_size = "Unknown"
                
                return {
                    "database_url": str(engine.url).replace(engine.url.password or "", "***"),
                    "pool_size": pool.size(),
                    "pool_checked_in": pool.checkedin(),
                    "pool_checked_out": pool.checkedout(),
                    "pool_overflow": pool.overflow(),
                    "table_count": len(table_names),
                    "database_size": db_size,
                    "engine_driver": engine.driver,
                    "dialect_name": engine.dialect.name
                }
        except SQLAlchemyError as e:
            logger.error(f"Database stats retrieval error: {str(e)}")
            raise DatabaseError(f"Failed to get database stats: {str(e)}", operation="get_database_stats")
    
    @staticmethod
    def cleanup_old_records(table_name: str, date_column: str, days_old: int = 30) -> int:
        """
        Clean up old records from a table.
        
        Args:
            table_name: Name of the table
            date_column: Name of the date column
            days_old: Number of days to keep records
            
        Returns:
            Number of deleted records
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            delete_query = f"""
                DELETE FROM {table_name} 
                WHERE {date_column} < :cutoff_date
            """
            
            with DatabaseUtils.get_transaction() as session:
                result = session.execute(text(delete_query), {"cutoff_date": cutoff_date})
                deleted_count = result.rowcount
                
                logger.info(f"Cleaned up {deleted_count} old records from {table_name}")
                return deleted_count
                
        except SQLAlchemyError as e:
            logger.error(f"Record cleanup error: {str(e)}")
            raise DatabaseError(f"Failed to cleanup old records: {str(e)}", operation="cleanup_old_records")
    
    @staticmethod
    def backup_table(table_name: str, backup_suffix: str = None) -> str:
        """
        Create a backup of a table.
        
        Args:
            table_name: Name of the table to backup
            backup_suffix: Suffix for backup table name
            
        Returns:
            Name of the backup table
        """
        try:
            if not backup_suffix:
                backup_suffix = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
            backup_table_name = f"{table_name}_backup_{backup_suffix}"
            
            # Create backup table (PostgreSQL specific)
            backup_query = f"""
                CREATE TABLE {backup_table_name} AS 
                SELECT * FROM {table_name}
            """
            
            with DatabaseUtils.get_transaction() as session:
                session.execute(text(backup_query))
                
                logger.info(f"Created backup table: {backup_table_name}")
                return backup_table_name
                
        except SQLAlchemyError as e:
            logger.error(f"Table backup error: {str(e)}")
            raise DatabaseError(f"Failed to backup table: {str(e)}", operation="backup_table")
    
    @staticmethod
    def optimize_table(table_name: str) -> None:
        """
        Optimize a database table.
        
        Args:
            table_name: Name of the table to optimize
        """
        try:
            # PostgreSQL specific optimization
            optimize_query = f"VACUUM ANALYZE {table_name}"
            
            with DatabaseUtils.get_db_session() as session:
                session.execute(text(optimize_query))
                
                logger.info(f"Optimized table: {table_name}")
                
        except SQLAlchemyError as e:
            logger.error(f"Table optimization error: {str(e)}")
            raise DatabaseError(f"Failed to optimize table: {str(e)}", operation="optimize_table")


class BaseRepository(Generic[ModelType]):
    """
    Base repository class for database operations.
    
    Provides common CRUD operations and query building
    for any model type.
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize repository with model class.
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
    
    def get_by_id(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Model instance or None
        """
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"Get by ID error: {str(e)}")
            raise DatabaseError(f"Failed to get record by ID: {str(e)}", operation="get_by_id")
    
    def get_by_field(self, db: Session, field: str, value: Any) -> Optional[ModelType]:
        """
        Get a record by field value.
        
        Args:
            db: Database session
            field: Field name
            value: Field value
            
        Returns:
            Model instance or None
        """
        try:
            filter_condition = getattr(self.model, field) == value
            return db.query(self.model).filter(filter_condition).first()
        except SQLAlchemyError as e:
            logger.error(f"Get by field error: {str(e)}")
            raise DatabaseError(f"Failed to get record by field: {str(e)}", operation="get_by_field")
    
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Get all records with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of model instances
        """
        try:
            return db.query(self.model).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Get all error: {str(e)}")
            raise DatabaseError(f"Failed to get all records: {str(e)}", operation="get_all")
    
    def create(self, db: Session, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Dictionary with field values
            
        Returns:
            Created model instance
        """
        try:
            db_obj = self.model(**obj_in)
            db.add(db_obj)
            db.flush()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Create integrity error: {str(e)}")
            raise ValidationError(f"Record already exists or violates constraints: {str(e)}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Create error: {str(e)}")
            raise DatabaseError(f"Failed to create record: {str(e)}", operation="create")
    
    def update(self, db: Session, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """
        Update an existing record.
        
        Args:
            db: Database session
            db_obj: Existing model instance
            obj_in: Dictionary with field values to update
            
        Returns:
            Updated model instance
        """
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            db.add(db_obj)
            db.flush()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Update integrity error: {str(e)}")
            raise ValidationError(f"Update violates constraints: {str(e)}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Update error: {str(e)}")
            raise DatabaseError(f"Failed to update record: {str(e)}", operation="update")
    
    def delete(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Delete a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Deleted model instance or None
        """
        try:
            obj = self.get_by_id(db, id)
            if obj:
                db.delete(obj)
                db.flush()
            return obj
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Delete error: {str(e)}")
            raise DatabaseError(f"Failed to delete record: {str(e)}", operation="delete")
    
    def count(self, db: Session) -> int:
        """
        Count all records.
        
        Args:
            db: Database session
            
        Returns:
            Number of records
        """
        try:
            return db.query(self.model).count()
        except SQLAlchemyError as e:
            logger.error(f"Count error: {str(e)}")
            raise DatabaseError(f"Failed to count records: {str(e)}", operation="count")
    
    def exists(self, db: Session, **kwargs) -> bool:
        """
        Check if a record exists with given field values.
        
        Args:
            db: Database session
            **kwargs: Field name/value pairs
            
        Returns:
            True if record exists, False otherwise
        """
        try:
            query = db.query(self.model)
            for field, value in kwargs.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
            return query.first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Exists check error: {str(e)}")
            raise DatabaseError(f"Failed to check record existence: {str(e)}", operation="exists")


class QueryBuilder:
    """
    Utility class for building complex database queries.
    
    Provides methods for building queries with filters,
    sorting, pagination, and joins.
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize query builder with model.
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
        self.query = None
    
    def base_query(self, db: Session) -> Query:
        """
        Get base query for the model.
        
        Args:
            db: Database session
            
        Returns:
            Base query
        """
        self.query = db.query(self.model)
        return self.query
    
    def filter_by(self, **kwargs) -> 'QueryBuilder':
        """
        Add filters to the query.
        
        Args:
            **kwargs: Field name/value pairs
            
        Returns:
            QueryBuilder instance for chaining
        """
        if self.query is None:
            raise DatabaseError("Query not initialized. Call base_query first.")
        
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                self.query = self.query.filter(getattr(self.model, field) == value)
        
        return self
    
    def filter_like(self, field: str, value: str) -> 'QueryBuilder':
        """
        Add LIKE filter to the query.
        
        Args:
            field: Field name
            value: Value to match
            
        Returns:
            QueryBuilder instance for chaining
        """
        if self.query is None:
            raise DatabaseError("Query not initialized. Call base_query first.")
        
        if hasattr(self.model, field):
            self.query = self.query.filter(getattr(self.model, field).like(f"%{value}%"))
        
        return self
    
    def filter_in(self, field: str, values: List[Any]) -> 'QueryBuilder':
        """
        Add IN filter to the query.
        
        Args:
            field: Field name
            values: List of values
            
        Returns:
            QueryBuilder instance for chaining
        """
        if self.query is None:
            raise DatabaseError("Query not initialized. Call base_query first.")
        
        if hasattr(self.model, field):
            self.query = self.query.filter(getattr(self.model, field).in_(values))
        
        return self
    
    def order_by(self, field: str, descending: bool = False) -> 'QueryBuilder':
        """
        Add ordering to the query.
        
        Args:
            field: Field name
            descending: Whether to sort in descending order
            
        Returns:
            QueryBuilder instance for chaining
        """
        if self.query is None:
            raise DatabaseError("Query not initialized. Call base_query first.")
        
        if hasattr(self.model, field):
            order_field = getattr(self.model, field)
            if descending:
                order_field = order_field.desc()
            self.query = self.query.order_by(order_field)
        
        return self
    
    def paginate(self, skip: int = 0, limit: int = 100) -> 'QueryBuilder':
        """
        Add pagination to the query.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            QueryBuilder instance for chaining
        """
        if self.query is None:
            raise DatabaseError("Query not initialized. Call base_query first.")
        
        self.query = self.query.offset(skip).limit(limit)
        return self
    
    def execute(self) -> List[ModelType]:
        """
        Execute the query and return results.
        
        Returns:
            List of model instances
        """
        if self.query is None:
            raise DatabaseError("Query not initialized. Call base_query first.")
        
        try:
            return self.query.all()
        except SQLAlchemyError as e:
            logger.error(f"Query execution error: {str(e)}")
            raise DatabaseError(f"Failed to execute query: {str(e)}", operation="execute_query")
    
    def count(self) -> int:
        """
        Count records in the query.
        
        Returns:
            Number of records
        """
        if self.query is None:
            raise DatabaseError("Query not initialized. Call base_query first.")
        
        try:
            return self.query.count()
        except SQLAlchemyError as e:
            logger.error(f"Query count error: {str(e)}")
            raise DatabaseError(f"Failed to count query results: {str(e)}", operation="count_query")
