"""
Cache helper module for the application.
Provides a simple in-memory cache with SQLite persistence.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
import logging
import threading

# Set up logging
logger = logging.getLogger(__name__)

# Define database path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache.db')

class Cache:
    """
    A simple cache implementation with in-memory storage and SQLite persistence.
    """
    
    def __init__(self):
        """Initialize the cache."""
        self._cache = {}  # In-memory cache
        self._lock = threading.Lock()  # For thread safety
        
        # Initialize SQLite database
        try:
            self._init_db()
            logger.info("Initialized SQLite cache at %s", DB_PATH)
        except Exception as e:
            logger.warning(f"Failed to initialize SQLite cache: {e}")
    
    def _init_db(self):
        """Initialize the SQLite database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create cache table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            expires_at TIMESTAMP
        )
        ''')
        
        # Create index on expires_at for faster cleanup
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires_at ON cache (expires_at)')
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        # Clean expired items on startup
        self._clean_expired()
    
    def _clean_expired(self):
        """Remove expired items from the database."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Delete expired items
            cursor.execute('DELETE FROM cache WHERE expires_at < ?', (datetime.now().isoformat(),))
            
            # Commit changes and close connection
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Error cleaning expired cache items: {e}")
    
    def get(self, key):
        """
        Get a value from the cache.
        
        Args:
            key (str): The cache key.
            
        Returns:
            The cached value or None if not found or expired.
        """
        # Try in-memory cache first
        with self._lock:
            if key in self._cache:
                item = self._cache[key]
                # Check if expired
                if 'expires_at' in item and datetime.now() > item['expires_at']:
                    del self._cache[key]
                else:
                    return item['value']
        
        # Fall back to SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get item from database
            cursor.execute('SELECT value, expires_at FROM cache WHERE key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                value, expires_at = result
                expires_at_dt = datetime.fromisoformat(expires_at)
                
                # Check if expired
                if datetime.now() > expires_at_dt:
                    self.delete(key)
                    return None
                
                # Parse JSON value
                parsed_value = json.loads(value)
                
                # Update in-memory cache
                with self._lock:
                    self._cache[key] = {
                        'value': parsed_value,
                        'expires_at': expires_at_dt
                    }
                
                return parsed_value
        except Exception as e:
            logger.warning(f"SQLite get error: {e}")
        
        return None
    
    def set(self, key, value, ex=3600):
        """
        Set a value in the cache.
        
        Args:
            key (str): The cache key.
            value: The value to cache.
            ex (int): Expiration time in seconds.
        """
        expires_at = datetime.now() + timedelta(seconds=ex)
        
        # Set in memory cache
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
        
        # Set in SQLite
        try:
            json_value = json.dumps(value)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Insert or replace in database
            cursor.execute(
                'INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)',
                (key, json_value, expires_at.isoformat())
            )
            
            # Commit changes and close connection
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"SQLite set error: {e}")
    
    def delete(self, key):
        """
        Delete a value from the cache.
        
        Args:
            key (str): The cache key.
        """
        # Remove from memory cache
        with self._lock:
            if key in self._cache:
                del self._cache[key]
        
        # Remove from SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Delete from database
            cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
            
            # Commit changes and close connection
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"SQLite delete error: {e}")

# Create a global cache instance
cache = Cache() 