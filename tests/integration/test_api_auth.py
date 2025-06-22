import pytest
from src.models import InteractionLog, User

# Sample protected route from app.py (choose one that has @jwt_required and @log_interaction)
# For this example, let's assume '/generate-exercise' is one such route.
# If it takes specific query params for a valid request, those should be included.
PROTECTED_ROUTE_FOR_LOGGING_TEST = '/generate-exercise?id=testnode&level=1'
# Ensure the 'id' and 'level' params are suitable for the actual endpoint logic,
# or adjust the route and params as needed for a 2xx response.


# --- Test Route Protection ---
def test_protected_route_with_valid_token(client, access_token):
    """Test accessing a protected route with a valid token."""
    # This test assumes PROTECTED_ROUTE_FOR_LOGGING_TEST exists and is protected
    # and that with a valid token it would return something other than 401/403.
    # The actual success status code (200, 201, etc.) depends on the route's implementation.
    # We also assume the dummy query params are enough for the route to not error out for other reasons.
    response = client.get(PROTECTED_ROUTE_FOR_LOGGING_TEST, headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert response.status_code != 401 # Should not be unauthorized
    assert response.status_code != 403 # Should not be forbidden
    # Add more specific assertions if you know the expected success status and response
    # For example, if it's expected to be 200:
    # assert response.status_code == 200

def test_protected_route_no_token(client):
    """Test accessing a protected route without a token."""
    response = client.get(PROTECTED_ROUTE_FOR_LOGGING_TEST)
    assert response.status_code == 401
    assert "Missing Authorization Header" in response.get_json()["msg"]

def test_protected_route_invalid_token(client):
    """Test accessing a protected route with an invalid token."""
    response = client.get(PROTECTED_ROUTE_FOR_LOGGING_TEST, headers={
        "Authorization": "Bearer invalidtoken"
    })
    assert response.status_code == 422 # Flask-JWT-Extended typically returns 422 for malformed tokens
    # Error message can vary, e.g., "Invalid header padding", "Not enough segments"
    # assert "Invalid token" in response.get_json()["msg"] # Or more specific error

# Note: Testing expired token requires time manipulation or setting short expiry.
# Flask-JWT-Extended handles this by default, returning 401 and "Token has expired".

# --- Test Interaction Logging ---
def test_interaction_log_created_on_protected_route_access(client, db_session, test_user, access_token):
    """Test that an InteractionLog entry is created when an authenticated user accesses a logged route."""

    # Pre-check: Ensure no logs for this user and endpoint yet (or count existing ones)
    initial_log_count = db_session.query(InteractionLog).filter_by(
        user_id=test_user.id,
        endpoint='generate_exercise' # request.endpoint for @app.route('/generate-exercise')
    ).count()

    # Access the protected (and logged) route
    response = client.get(PROTECTED_ROUTE_FOR_LOGGING_TEST, headers={
        "Authorization": f"Bearer {access_token}"
    })

    # We expect the route to succeed (not 401/403) for the log to be made by the decorator.
    # If the route itself has issues (e.g. 500, 404 for other reasons), logging might still occur or not
    # depending on decorator implementation. The current decorator logs after route execution.
    assert response.status_code != 401
    # For this test to be robust, it's best if PROTECTED_ROUTE_FOR_LOGGING_TEST returns a success code (e.g. 200)
    # when properly authenticated and with correct parameters.

    # Verify a new log entry was created
    final_log_count = db_session.query(InteractionLog).filter_by(
        user_id=test_user.id,
        endpoint='generate_exercise'
    ).count()
    assert final_log_count == initial_log_count + 1

    # Verify details of the last log entry (optional, but good)
    log_entry = db_session.query(InteractionLog).filter_by(
        user_id=test_user.id,
        endpoint='generate_exercise'
    ).order_by(InteractionLog.id.desc()).first()

    assert log_entry is not None
    assert log_entry.user_id == test_user.id
    assert log_entry.endpoint == 'generate_exercise' # Flask endpoint name
    if PROTECTED_ROUTE_FOR_LOGGING_TEST.split('?')[1]: # If there were query params
        expected_payload = dict(arg.split('=') for arg in PROTECTED_ROUTE_FOR_LOGGING_TEST.split('?')[1].split('&'))
        # The decorator stores args as dict. Convert numeric strings if necessary for direct comparison.
        # e.g. {'id': 'testnode', 'level': '1'}
        # Adjust this check based on how your decorator stringifies/stores GET params.
        assert log_entry.payload == expected_payload


def test_interaction_log_for_auth_me(client, db_session, test_user, access_token):
    """Test that InteractionLog is created for /auth/me."""
    initial_log_count = db_session.query(InteractionLog).filter_by(
        user_id=test_user.id,
        endpoint='auth.me' # Endpoint for blueprint routes is 'blueprint_name.view_function_name'
    ).count()

    response = client.get('/auth/me', headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200

    final_log_count = db_session.query(InteractionLog).filter_by(
        user_id=test_user.id,
        endpoint='auth.me'
    ).count()
    assert final_log_count == initial_log_count + 1

    log_entry = db_session.query(InteractionLog).filter_by(user_id=test_user.id, endpoint='auth.me').order_by(InteractionLog.id.desc()).first()
    assert log_entry is not None
    assert log_entry.payload is None # /auth/me is GET with no payload typically logged by current decorator for GET

# Add more tests for other logged routes if payload structure or conditions differ.
# e.g., POST request to /continue-exercise with JSON payload.
# def test_interaction_log_for_continue_exercise(client, db_session, test_user, access_token):
#     exercise_payload = {"node_id": "some_node", "level": 1, "message": "hello", "history": []}
#     initial_log_count = db_session.query(InteractionLog).filter_by(user_id=test_user.id, endpoint='continue_exercise').count()
#
#     response = client.post('/continue-exercise', json=exercise_payload, headers={"Authorization": f"Bearer {access_token}"})
#     assert response.status_code == 200 # Or whatever success code is
#
#     # ... assertions for log count and content, including checking log_entry.payload == exercise_payload
#     ...
