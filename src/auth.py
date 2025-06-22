from flask import Blueprint, request, jsonify
from passlib.hash import bcrypt # Using passlib as planned
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from sqlalchemy.exc import IntegrityError
import datetime

from .models import User
from .database import SessionLocal, get_db # Assuming get_db is preferred
from .decorators import log_interaction # Import the interaction logger decorator

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Helper function to get a database session
def get_session():
    return next(get_db())

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"msg": "Missing username, email, or password"}), 400

    db = get_session()
    try:
        # Check if user already exists
        if db.query(User).filter((User.username == username) | (User.email == email)).first():
            return jsonify({"msg": "Username or email already exists"}), 409

        hashed_password = bcrypt.hash(password) # Use bcrypt for hashing
        new_user = User(username=username, email=email, password_hash=hashed_password)

        db.add(new_user)
        db.commit()
        db.refresh(new_user) # To get ID, created_at, etc.

        return jsonify({
            "msg": "User created successfully",
            "user": {"id": new_user.id, "username": new_user.username, "email": new_user.email}
        }), 201

    except IntegrityError: # Handles potential race conditions if unique constraints are violated
        db.rollback()
        return jsonify({"msg": "Database integrity error, possibly duplicate username or email"}), 409
    except Exception as e:
        db.rollback()
        return jsonify({"msg": "An error occurred during signup", "error": str(e)}), 500
    finally:
        db.close()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    login_identifier = data.get('login_identifier') # Can be username or email
    password = data.get('password')

    if not login_identifier or not password:
        return jsonify({"msg": "Missing login identifier or password"}), 400

    db = get_session()
    try:
        user = db.query(User).filter((User.username == login_identifier) | (User.email == login_identifier)).first()

        if user and bcrypt.verify(password, user.password_hash): # Use bcrypt for verification
            user.last_login = datetime.datetime.now(datetime.timezone.utc)
            db.commit()

            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            return jsonify(access_token=access_token, refresh_token=refresh_token), 200
        else:
            return jsonify({"msg": "Bad username/email or password"}), 401
    except Exception as e:
        db.rollback() # Rollback in case of other errors like DB connection issue
        return jsonify({"msg": "An error occurred during login", "error": str(e)}), 500
    finally:
        db.close()

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
@log_interaction
def refresh():
    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id)
    return jsonify(access_token=new_access_token), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
@log_interaction
def me():
    current_user_id = get_jwt_identity()
    db = get_session()
    try:
        user = db.query(User).filter(User.id == current_user_id).first()
        if not user:
            return jsonify({"msg": "User not found"}), 404

        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }), 200
    except Exception as e:
        return jsonify({"msg": "An error occurred", "error": str(e)}), 500
    finally:
        db.close()

# Optional: Logout (if using denylist/blocklist for tokens)
# @auth_bp.route('/logout', methods=['POST'])
# @jwt_required()
# def logout():
#     jti = get_jwt()["jti"]
#     # Add jti to a denylist (e.g., in Redis or a database table)
#     # BLOCKLIST.add(jti) # Example if BLOCKLIST is a set
#     return jsonify(msg="Access token revoked"), 200

# Note: For a production setup with token blocklisting, you'd need to implement
# a persistent blocklist store and check against it. Flask-JWT-Extended provides
# hooks for this (e.g., token_in_blocklist_loader).
# For simplicity, full blocklisting is not implemented here.
# Refresh token revocation would also need similar handling.
