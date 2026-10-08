"""
Callbacks Flask-JWT-Extended.
"""
from flask import jsonify
from flask_jwt_extended import get_jwt

from extensions import jwt
from models import User, TokenBlocklist


@jwt.user_identity_loader
def user_identity_lookup(user):
    if isinstance(user, User):
        return str(user.id)
    return str(user)


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(int(identity))


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return TokenBlocklist.query.filter_by(jti=jti).first() is not None


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': 'Token expiré', 'code': 'token_expired'}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'error': 'Token invalide', 'code': 'token_invalid'}), 401


@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'error': 'Token manquant', 'code': 'authorization_required'}), 401


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': 'Token révoqué', 'code': 'token_revoked'}), 401