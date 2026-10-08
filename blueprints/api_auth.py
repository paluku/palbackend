"""
API d'authentification JWT pour Flutter / mobile.
"""
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt, current_user,
)

from extensions import db, limiter
from models import User, TokenBlocklist
from logs_utils import log_action
from email_utils import envoyer_reset_password

api_auth_bp = Blueprint('api_auth', __name__, url_prefix='/api/auth')


# ==================== INSCRIPTION ====================
@api_auth_bp.route('/register', methods=['POST'], strict_slashes=False)
@limiter.limit("5 per hour")
def register():
    data = request.json or {}
    nom = (data.get('nom') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    erreurs = []
    if not nom:
        erreurs.append('Le nom est obligatoire')
    if not email:
        erreurs.append("L'email est obligatoire")
    if len(password) < 6:
        erreurs.append('Mot de passe : 6 caractères minimum')

    if erreurs:
        return jsonify({'error': ' | '.join(erreurs)}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Cet email est déjà utilisé'}), 409

    user = User(nom=nom, email=email, role='user')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    log_action('api_register', f'Nouveau : {email}', user=user)

    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
    }), 201


# ==================== CONNEXION ====================
@api_auth_bp.route('/login', methods=['POST'], strict_slashes=False)
@limiter.limit("10 per minute")
def login():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email et mot de passe obligatoires'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        if user:
            user.failed_logins = (user.failed_logins or 0) + 1
            db.session.commit()
        log_action('api_login_failed', f'Échec : {email}')
        return jsonify({'error': 'Email ou mot de passe incorrect'}), 401

    user.failed_logins = 0
    user.last_login = datetime.utcnow()
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    log_action('api_login', f'Connexion : {email}', user=user)

    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
    })


# ==================== RAFRAÎCHIR ====================
@api_auth_bp.route('/refresh', methods=['POST'], strict_slashes=False)
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)

    return jsonify({
        'success': True,
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
    })


# ==================== DÉCONNEXION ====================
@api_auth_bp.route('/logout', methods=['POST'], strict_slashes=False)
@jwt_required(verify_type=False)
def logout():
    jwt_data = get_jwt()
    jti = jwt_data['jti']
    token_type = jwt_data['type']

    db.session.add(TokenBlocklist(jti=jti, type=token_type))
    db.session.commit()

    log_action('api_logout', f'Token révoqué ({token_type})')

    return jsonify({'success': True, 'message': 'Déconnexion réussie'})


# ==================== MON PROFIL ====================
@api_auth_bp.route('/me', methods=['GET'], strict_slashes=False)
@jwt_required()
def me():
    return jsonify({
        'success': True,
        'user': current_user.to_dict(),
    })


# ==================== CHANGER MOT DE PASSE ====================
@api_auth_bp.route('/change-password', methods=['POST'], strict_slashes=False)
@jwt_required()
def change_password():
    data = request.json or {}
    current_pwd = data.get('current_password', '')
    new_pwd = data.get('new_password', '')

    if not current_user.check_password(current_pwd):
        return jsonify({'error': 'Mot de passe actuel incorrect'}), 400

    if len(new_pwd) < 6:
        return jsonify({'error': '6 caractères minimum'}), 400

    current_user.set_password(new_pwd)
    db.session.commit()

    log_action('api_password_changed', current_user.email, user=current_user)

    return jsonify({'success': True, 'message': 'Mot de passe modifié'})


# ==================== MOT DE PASSE OUBLIÉ ====================
@api_auth_bp.route('/forgot-password', methods=['POST'], strict_slashes=False)
@limiter.limit("3 per hour")
def forgot_password():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()

    user = User.query.filter_by(email=email).first()
    if user:
        try:
            envoyer_reset_password(user)
        except Exception as e:
            print(f"⚠️ Erreur email : {e}")

    return jsonify({
        'success': True,
        'message': 'Si un compte existe, un email a été envoyé.',
    })