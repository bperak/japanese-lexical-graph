from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL # Import DATABASE_URL from root config.py

# Create the SQLAlchemy engine
# The pool_pre_ping argument will help with connection issues
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create a SessionLocal class, which will be a factory for new Session objects
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative class definitions
Base = declarative_base()

# Optional: function to get a DB session. This can be used as a dependency in routes.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Optional: function to create all tables (useful for initial setup without Alembic, or for tests)
# For production, Alembic migrations are preferred.
def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    # This can be used to quickly initialize the database if needed,
    # but Alembic should be the primary way to manage schema.
    print("Initializing database schema based on models...")
    # Make sure all models are imported here before calling create_all!
    # e.g. from . import models # Assuming models.py is in the same directory
    # init_db() # Uncomment if you have models and want to create tables directly
    print(f"Database engine configured for: {engine.url}")
    print("If you have models, uncomment the import and init_db() call to create tables.")
    print("For production, use Alembic migrations.")
