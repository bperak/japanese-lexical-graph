import pytest
from flask import jsonify
from passlib.hash import bcrypt

from src.models import User
from src.auth import auth_bp # Assuming auth_bp is accessible for some tests if needed, or test via client

# --- Test User Model ---
def test_user_password_hashing(test_user_data):
    """Test that password hashing and verification work."""
    password = test_user_data["password"]
    hashed_password = bcrypt.hash(password)
    assert bcrypt.verify(password, hashed_password)
    assert not bcrypt.verify("wrongpassword", hashed_password)

# --- Test /auth/signup ---
def test_signup_success(client, db_session, test_user_data):
    """Test successful user signup."""
    response = client.post('/auth/signup', json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "newpassword123"
    })
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["msg"] == "User created successfully"
    assert json_data["user"]["username"] == "newuser"

    # Verify user in DB
    user = db_session.query(User).filter_by(username="newuser").first()
    assert user is not None
    assert user.email == "new@example.com"
    assert bcrypt.verify("newpassword123", user.password_hash)

def test_signup_duplicate_username(client, test_user, test_user_data):
    """Test signup with a duplicate username."""
    response = client.post('/auth/signup', json={
        "username": test_user_data["username"], # Existing username
        "email": "another@example.com",
        "password": "password123"
    })
    assert response.status_code == 409
    assert "Username or email already exists" in response.get_json()["msg"]

def test_signup_duplicate_email(client, test_user, test_user_data):
    """Test signup with a duplicate email."""
    response = client.post('/auth/signup', json={
        "username": "anotheruser",
        "email": test_user_data["email"], # Existing email
        "password": "password123"
    })
    assert response.status_code == 409
    assert "Username or email already exists" in response.get_json()["msg"]

def test_signup_missing_fields(client):
    """Test signup with missing fields."""
    response = client.post('/auth/signup', json={"username": "useronly"})
    assert response.status_code == 400
    assert "Missing username, email, or password" in response.get_json()["msg"]

# --- Test /auth/login ---
def test_login_success(client, test_user, test_user_data):
    """Test successful login with correct credentials."""
    response = client.post('/auth/login', json={
        "login_identifier": test_user_data["username"],
        "password": test_user_data["password"]
    })
    assert response.status_code == 200
    json_data = response.get_json()
    assert "access_token" in json_data
    assert "refresh_token" in json_data

def test_login_success_with_email(client, test_user, test_user_data):
    """Test successful login using email."""
    response = client.post('/auth/login', json={
        "login_identifier": test_user_data["email"],
        "password": test_user_data["password"]
    })
    assert response.status_code == 200
    json_data = response.get_json()
    assert "access_token" in json_data

def test_login_wrong_password(client, test_user, test_user_data):
    """Test login with incorrect password."""
    response = client.post('/auth/login', json={
        "login_identifier": test_user_data["username"],
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Bad username/email or password" in response.get_json()["msg"]

def test_login_nonexistent_user(client):
    """Test login with a non-existent user."""
    response = client.post('/auth/login', json={
        "login_identifier": "nosuchuser",
        "password": "password"
    })
    assert response.status_code == 401 # Or could be 404 depending on desired behavior
    assert "Bad username/email or password" in response.get_json()["msg"]

def test_login_missing_fields(client):
    """Test login with missing fields."""
    response = client.post('/auth/login', json={"login_identifier": "useronly"})
    assert response.status_code == 400
    assert "Missing login identifier or password" in response.get_json()["msg"]


# --- Test /auth/refresh ---
def test_refresh_token_success(client, test_user):
    """Test successful token refresh."""
    # First, log in to get a refresh token
    login_resp = client.post('/auth/login', json={
        "login_identifier": test_user.username,
        "password": "password123" # Assuming 'password123' is the password for test_user fixture
    })
    refresh_token = login_resp.get_json()["refresh_token"]

    response = client.post('/auth/refresh', headers={
        "Authorization": f"Bearer {refresh_token}"
    })
    assert response.status_code == 200
    assert "access_token" in response.get_json()

def test_refresh_with_access_token(client, access_token):
    """Test attempting to refresh with an access token (should fail)."""
    response = client.post('/auth/refresh', headers={
        "Authorization": f"Bearer {access_token}" # Using access token
    })
    # Expected behavior for Flask-JWT-Extended is 422 if token type is wrong
    assert response.status_code == 422
    assert "Only refresh tokens are allowed" in response.get_json()["msg"]


# --- Test /auth/me ---
def test_get_me_success(client, access_token, test_user):
    """Test successfully getting user details."""
    response = client.get('/auth/me', headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["id"] == test_user.id
    assert json_data["username"] == test_user.username
    assert json_data["email"] == test_user.email

def test_get_me_no_token(client):
    """Test accessing /me without a token."""
    response = client.get('/auth/me')
    assert response.status_code == 401 # Missing Authorization Header
    assert "Missing Authorization Header" in response.get_json()["msg"]

def test_get_me_invalid_token(client):
    """Test accessing /me with an invalid token."""
    response = client.get('/auth/me', headers={
        "Authorization": "Bearer invalidtoken"
    })
    assert response.status_code == 422 # Invalid token format / signature
    assert "Invalid header padding" in response.get_json()["msg"] # Example error, may vary
                                                                # Actual message might be "Not enough segments", "Invalid token" etc.
                                                                # depending on how Flask-JWT-Extended decodes it.
                                                                # For "invalidtoken", it's likely a padding or segment error.
                                                                # A more robust check would be on the error type if possible.
                                                                # For now, checking status code is primary.

# Note: Testing for expired tokens requires manipulating time, which can be complex.
# It's often handled by setting very short expiry times for specific tests if needed.
# Flask-JWT-Extended handles expired token errors by default.
