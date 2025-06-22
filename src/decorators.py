from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
import datetime

from .models import InteractionLog
from .database import SessionLocal # Using SessionLocal directly for simplicity here

def log_interaction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Ensure JWT is present and valid before proceeding to log
        # This also makes current_user_id available if called after @jwt_required
        # verify_jwt_in_request() # This would raise error if no JWT, which is fine if decorator is after @jwt_required

        # Call the original route function first
        response = func(*args, **kwargs)

        # Proceed to log only if the request was likely successful (e.g. response is not an error)
        # For simplicity, we'll log if a JWT identity is found after the route execution.
        # A more robust check might inspect the response status code.

        current_user_id = None
        try:
            # We need to ensure JWT is processed to get identity.
            # If @jwt_required is used, identity is already available.
            # If this decorator is used on a public route by mistake, we should handle it.
            verify_jwt_in_request(optional=True) # Check if JWT is there, don't fail if not
            jwt_identity = get_jwt_identity()
            if jwt_identity:
                current_user_id = jwt_identity
        except Exception as e:
            # Could log this error if needed, but for now, just means no user to associate
            print(f"Could not get JWT identity for logging: {e}") # Replace with actual logger
            pass # Continue without logging if no user identity from JWT

        if current_user_id:
            db = None
            try:
                db = SessionLocal()

                # Determine the payload
                payload_data = None
                if request.method in ['POST', 'PUT', 'PATCH']:
                    payload_data = request.get_json(silent=True)
                elif request.method == 'GET':
                    # For GET, query parameters might be more relevant than a body
                    if request.args:
                        payload_data = dict(request.args)

                log_entry = InteractionLog(
                    user_id=current_user_id,
                    endpoint=request.endpoint,
                    payload=payload_data,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                db.add(log_entry)
                db.commit()
            except Exception as e:
                if db:
                    db.rollback()
                # Log this error to server logs, don't fail the request itself
                print(f"Error logging interaction: {str(e)}") # Replace with actual logger
            finally:
                if db:
                    db.close()

        return response
    return wrapper
