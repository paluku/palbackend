"""
API utilisateurs (JWT).
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from extensions import db
from models import User

api_users_bp = Blueprint('api_users', __name__, url_prefix='/api/users')


def _admin_only():
    return current_user.is_admin


@api_users_bp.route('', methods=['GET'], strict_slashes=False)
@jwt_required()
def liste_users():
    if not _admin_only():
        return jsonify({'error': 'Accès interdit'}), 403

    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({
        'success': True,
        'total': len(users),
        'users': [u.to_dict() for u in users],
    })


@api_users_bp.route('/<int:user_id>', methods=['GET'], strict_slashes=False)
@jwt_required()
def detail_user(user_id):
    if not _admin_only() and current_user.id != user_id:
        return jsonify({'error': 'Accès interdit'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    return jsonify({'success': True, 'user': user.to_dict()})


@api_users_bp.route('/<int:user_id>/role', methods=['PUT'], strict_slashes=False)
@jwt_required()
def change_role(user_id):
    if not _admin_only():
        return jsonify({'error': 'Accès interdit'}), 403

    data = request.json or {}
    new_role = data.get('role', 'user')

    if new_role not in ('user', 'moderator', 'admin'):
        return jsonify({'error': 'Rôle invalide'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    user.role = new_role
    db.session.commit()

    return jsonify({'success': True, 'user': user.to_dict()})


@api_users_bp.route('/<int:user_id>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def delete_user(user_id):
    if not _admin_only():
        return jsonify({'error': 'Accès interdit'}), 403

    if user_id == current_user.id:
        return jsonify({'error': 'Vous ne pouvez pas vous supprimer'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Utilisateur supprimé'})