from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Base

_db_url = settings.database_url
_engine_kwargs = {"pool_pre_ping": True}
if _db_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = settings.database.pool_size
    _engine_kwargs["max_overflow"] = settings.database.max_overflow
    _engine_kwargs["echo"] = settings.database.echo

engine = create_engine(_db_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
