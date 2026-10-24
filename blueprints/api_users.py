

"""API admin — gestion des utilisateurs."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from extensions import db
from models import User, Recette, Marchandise, Depense

api_users_bp = Blueprint('api_users', __name__, url_prefix='/api/users')


def _is_admin():
    return getattr(current_user, 'is_admin', False)


@api_users_bp.route('', methods=['GET'], strict_slashes=False)
@jwt_required()
def list_users():
    if not _is_admin():
        return jsonify({'error': "Accès réservé à l'administrateur"}), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({
        'success': True,
        'count': len(users),
        'users': [u.to_dict() for u in users],
    })


@api_users_bp.route('/<int:user_id>', methods=['GET'], strict_slashes=False)
@jwt_required()
def get_user(user_id):
    if not _is_admin() and current_user.id != user_id:
        return jsonify({'error': 'Non autorisé'}), 403
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    return jsonify({'success': True, 'user': u.to_dict()})


@api_users_bp.route('/<int:user_id>/role', methods=['PUT'], strict_slashes=False)
@jwt_required()
def set_role(user_id):
    if not _is_admin():
        return jsonify({'error': "Accès réservé à l'administrateur"}), 403
    if current_user.id == user_id:
        return jsonify({'error': 'Impossible de changer votre propre rôle'}), 400

    data = request.get_json(silent=True) or {}
    role = (data.get('role') or '').strip().lower()
    if role not in ('user', 'admin'):
        return jsonify({'error': 'Rôle invalide'}), 400

    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    u.role = role
    db.session.commit()
    return jsonify({'success': True, 'user': u.to_dict()})


@api_users_bp.route('/<int:user_id>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def delete_user(user_id):
    if not _is_admin():
        return jsonify({'error': "Accès réservé à l'administrateur"}), 403
    if current_user.id == user_id:
        return jsonify({'error': 'Impossible de vous supprimer vous-même'}), 400

    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    Recette.query.filter_by(user_id=user_id).delete()
    Marchandise.query.filter_by(user_id=user_id).delete()
    Depense.query.filter_by(user_id=user_id).delete()
    db.session.delete(u)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Utilisateur supprimé'})