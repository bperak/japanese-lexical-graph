from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # For server-side default timestamps

from .database import Base # Relative import from src.database

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationship to InteractionLog (one-to-many: one User can have many InteractionLogs)
    interaction_logs = relationship("InteractionLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    endpoint = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=True) # Request payload or relevant data
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationship back to User (many-to-one: many InteractionLogs belong to one User)
    user = relationship("User", back_populates="interaction_logs")

    def __repr__(self):
        return f"<InteractionLog(id={self.id}, user_id={self.user_id}, endpoint='{self.endpoint}', timestamp='{self.timestamp}')>"

# Optional: You might want to add other models here as your application grows.

# To ensure models are registered with Base, you might need to import them somewhere
# where Base is defined or used, e.g., in database.py or your main app file if you
# were to call Base.metadata.create_all(). For Alembic, importing Base in env.py and
# setting target_metadata = Base.metadata is usually sufficient for discovery.
# For now, we expect alembic/env.py to correctly pick up these models via Base.metadata.
