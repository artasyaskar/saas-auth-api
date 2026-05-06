"""
Base repository class.

Provides common database operations and CRUD functionality
that can be inherited by specific repositories.
"""

from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db

# TODO: Add proper error handling for database operations
# TODO: Implement caching layer for frequently accessed data
# TODO: Add transaction management

ModelType = TypeVar("ModelType", bound=declarative_base())


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.
    
    This class provides a foundation for all repositories with
    standard database operations like create, read, update, delete.
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def create(self, obj_data: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            obj_data: Dictionary with model field values
            
        Returns:
            Created model instance
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_obj = self.model(**obj_data)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            # TODO: Add proper logging here
            raise e
    
    def get(self, id: int) -> Optional[ModelType]:
        """
        Get record by ID.
        
        Args:
            id: Primary key of the record
            
        Returns:
            Model instance or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> List[ModelType]:
        """
        Get multiple records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort_by: Field name to sort by
            sort_desc: Sort in descending order if True
            
        Returns:
            List of model instances
        """
        query = self.db.query(self.model)
        
        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            sort_field = getattr(self.model, sort_by)
            if sort_desc:
                query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(asc(sort_field))
        
        # Apply pagination
        return query.offset(skip).limit(limit).all()
    
    def update(self, id: int, obj_data: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update a record by ID.
        
        Args:
            id: Primary key of the record
            obj_data: Dictionary with updated field values
            
        Returns:
            Updated model instance or None if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_obj = self.get(id)
            if db_obj:
                for field, value in obj_data.items():
                    if hasattr(db_obj, field):
                        setattr(db_obj, field, value)
                
                self.db.commit()
                self.db.refresh(db_obj)
                return db_obj
            return None
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, id: int) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: Primary key of the record
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_obj = self.get(id)
            if db_obj:
                self.db.delete(db_obj)
                self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """
        Get record by field value.
        
        Args:
            field_name: Name of the field to query
            value: Value to match
            
        Returns:
            Model instance or None if not found
        """
        if not hasattr(self.model, field_name):
            return None
        
        field = getattr(self.model, field_name)
        return self.db.query(self.model).filter(field == value).first()
    
    def get_by_fields(self, filters: Dict[str, Any]) -> Optional[ModelType]:
        """
        Get record by multiple field values.
        
        Args:
            filters: Dictionary of field names and values to match
            
        Returns:
            Model instance or None if not found
        """
        query = self.db.query(self.model)
        
        for field_name, value in filters.items():
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                query = query.filter(field == value)
        
        return query.first()
    
    def exists(self, id: int) -> bool:
        """
        Check if record exists by ID.
        
        Args:
            id: Primary key of the record
            
        Returns:
            True if exists, False otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first() is not None
    
    def exists_by_field(self, field_name: str, value: Any) -> bool:
        """
        Check if record exists by field value.
        
        Args:
            field_name: Name of the field to query
            value: Value to match
            
        Returns:
            True if exists, False otherwise
        """
        if not hasattr(self.model, field_name):
            return False
        
        field = getattr(self.model, field_name)
        return self.db.query(self.model).filter(field == value).first() is not None
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filters.
        
        Args:
            filters: Dictionary of field names and values to match
            
        Returns:
            Number of matching records
        """
        query = self.db.query(self.model)
        
        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    query = query.filter(field == value)
        
        return query.count()
    
    def search(
        self, 
        search_term: str, 
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Search records by term across multiple fields.
        
        Args:
            search_term: Term to search for
            search_fields: List of field names to search in
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching model instances
        """
        query = self.db.query(self.model)
        
        # Build search conditions
        search_conditions = []
        for field_name in search_fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                search_conditions.append(field.ilike(f"%{search_term}%"))
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
        
        return query.offset(skip).limit(limit).all()
