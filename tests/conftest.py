import sys
from types import ModuleType

# Stub out heavy/optional external dependencies so unit tests can run
# in environments where these packages are not installed.
for mod_name in ["google.generativeai", "SPARQLWrapper"]:
    if mod_name not in sys.modules:
        dummy_module = ModuleType(mod_name)
        # Add minimal attributes used in code paths during import
        if mod_name == "google.generativeai":
            def _noop(*args, **kwargs):
                return None
            dummy_module.configure = _noop  # type: ignore[attr-defined]
            class _DummyModel:
                def generate_content(self, *args, **kwargs):
                    raise RuntimeError("Dummy GenerativeModel should be patched in tests.")
            dummy_module.GenerativeModel = _DummyModel  # type: ignore[attr-defined]
        sys.modules[mod_name] = dummy_module

import pytest
from app import app as flask_app  # Import your Flask app instance
from src.database import Base, engine, SessionLocal, get_db
from src.models import User, InteractionLog
from passlib.hash import bcrypt
from flask_jwt_extended import create_access_token
import os
import tempfile

# Override the DATABASE_URL for testing if not already set by environment
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:") # Default to in-memory SQLite for simplicity

@pytest.fixture(scope="session")
def app():
    """Session-wide test Flask application."""

    # Critical: Ensure the app uses a test database configuration.
    # If your app directly uses DATABASE_URL from config.py, ensure config.py can pick up a test-specific URL.
    # For this example, we'll assume app.py's config loading can be influenced by env vars
    # or we reconfigure it here if necessary.
    # A common pattern is to have a create_app(config_name) factory.
    # Here, we'll try to set it for the imported flask_app.

    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL, # For SQLAlchemy if used directly by Flask extensions
        "JWT_SECRET_KEY": "test-jwt-secret-key", # Use a fixed test key
        "SECRET_KEY": "test-flask-secret-key",
    })

    # If your app's SQLAlchemy engine is hardcoded via config.DATABASE_URL,
    # you might need to adjust how 'engine' and 'SessionLocal' in src.database are configured for tests.
    # This fixture assumes src.database.engine will use the TEST_DATABASE_URL when app.config is set.
    # This might require modification in src.database.py to be test-aware, or by patching it.
    # For now, let's assume direct modification or that config.py reads TEST_DATABASE_URL if TESTING is True.

    # For simplicity in this example, if DATABASE_URL in config.py is used directly to create src.database.engine,
    # tests would need to ensure that os.environ['DATABASE_URL'] is set to TEST_DATABASE_URL *before* src.database is imported.
    # A cleaner way is for src.database.engine to be initialized within the app context or via a factory.

    # The provided `src.database.engine` is created at import time using `config.DATABASE_URL`.
    # To make it testable with SQLite in-memory without complex patching or app factories,
    # we will re-initialize the engine and SessionLocal for the test session if using SQLite.

    global engine, SessionLocal, Base

    original_engine = engine
    original_session_local = SessionLocal

    if TEST_DATABASE_URL.startswith("sqlite:///:memory:"):
        from sqlalchemy import create_engine
        new_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}) # SQLite specific
        new_session_local = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)

        # Monkey patch the engine and SessionLocal in src.database for the duration of the tests
        import src.database
        src.database.engine = new_engine
        src.database.SessionLocal = new_session_local

        Base.metadata.create_all(bind=new_engine) # Create tables for in-memory SQLite

        yield flask_app

        Base.metadata.drop_all(bind=new_engine)
        src.database.engine = original_engine # Restore original engine
        src.database.SessionLocal = original_session_local # Restore original SessionLocal
    else: # Assuming a persistent test database (e.g., a separate PostgreSQL test DB)
        # Ensure your config.py loads TEST_DATABASE_URL if set, otherwise this won't point to test DB
        # For persistent DB, tables should be managed by Alembic or created/dropped here.
        # This example assumes Alembic handles the persistent test DB schema.
        # If not using Alembic for test DB, uncomment:
        # Base.metadata.create_all(bind=engine)
        yield flask_app
        # Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function") # Changed to function scope for DB reset per test
def db_session(app):
    """Yields a SQLAlchemy session for a test. Rolls back transactions."""

    # Get the potentially patched SessionLocal
    current_session_local = SessionLocal

    connection = current_session_local.bind.connect()
    transaction = connection.begin()
    session = current_session_local(bind=connection)

    # If not in-memory, ensure tables are clean or reset them.
    # For in-memory, create_all is handled in app fixture.
    # For persistent, this assumes schema exists. For clean state, might need to delete from tables.
    if not TEST_DATABASE_URL.startswith("sqlite:///:memory:"):
         # A more robust way for persistent DBs is to use database transactions per test
         # and roll them back, or use a library like pytest-postgresql.
         # For now, deleting data from tables for function-scoped isolation.
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def test_user_data():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }

@pytest.fixture
def test_user(db_session, test_user_data):
    """Creates a user in the database for testing."""
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        password_hash=bcrypt.hash(test_user_data["password"])
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def access_token(test_user):
    """Generates an access token for the test_user."""
    # Needs app context to create token if create_access_token uses current_app
    from app import app as current_flask_app
    with current_flask_app.app_context():
        token = create_access_token(identity=test_user.id)
    return token