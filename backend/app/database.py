from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

# If using Neon, we want a connection pool that handles serverless cold starts efficiently.
# Using pool_pre_ping to test connections before handing them out.
# Using pool_recycle to drop connections older than 5 minutes.
# Small pool_size because serverless instances are single-threaded/short-lived.

engine_kwargs = {}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
else:
    engine_kwargs = {
        "pool_size": 2,
        "max_overflow": 5,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
