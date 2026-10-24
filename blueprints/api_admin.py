"""API admin — stats globales + suppression recettes/marchandises/dépenses."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, current_user

from extensions import db
from models import User, Recette, Marchandise, Depense

api_admin_bp = Blueprint('api_admin', __name__, url_prefix='/api/admin')


def _is_admin():
    return getattr(current_user, 'is_admin', False)


@api_admin_bp.route('/stats', methods=['GET'], strict_slashes=False)
@jwt_required()
def stats():
    if not _is_admin():
        return jsonify({'error': "Accès réservé à l'administrateur"}), 403

    users = User.query.all()
    recettes = Recette.query.order_by(Recette.created_at.desc()).all()
    marchandises = Marchandise.query.order_by(Marchandise.created_at.desc()).all()
    depenses = Depense.query.order_by(Depense.created_at.desc()).all()

    total_recettes = sum(r.montant for r in recettes)
    total_brut = sum(m.prix_total_brut for m in marchandises)
    total_net = sum(m.prix_total_net for m in marchandises)
    total_depenses = sum(d.montant for d in depenses)

    return jsonify({
        'success': True,
        'kpi': {
            'nb_users': len(users),
            'total_recettes': round(total_recettes, 2),
            'nb_marchandises': len(marchandises),
            'total_net': round(total_net, 2),
            'total_depenses': round(total_depenses, 2),
            'total_brut_march': round(total_brut, 2),
        },
        'recettes': [r.to_dict() for r in recettes],
        'marchandises': [m.to_dict() for m in marchandises],
        'depenses': [d.to_dict() for d in depenses],
    })


@api_admin_bp.route('/recettes/<int:r_id>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def delete_recette(r_id):
    if not _is_admin():
        return jsonify({'error': 'Non autorisé'}), 403
    r = db.session.get(Recette, r_id)
    if not r:
        return jsonify({'error': 'Introuvable'}), 404
    db.session.delete(r)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Recette supprimée'})


@api_admin_bp.route('/marchandises/<int:m_id>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def delete_marchandise(m_id):
    if not _is_admin():
        return jsonify({'error': 'Non autorisé'}), 403
    m = db.session.get(Marchandise, m_id)
    if not m:
        return jsonify({'error': 'Introuvable'}), 404
    db.session.delete(m)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Marchandise supprimée'})


@api_admin_bp.route('/depenses/<int:d_id>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def delete_depense(d_id):
    if not _is_admin():
        return jsonify({'error': 'Non autorisé'}), 403
    d = db.session.get(Depense, d_id)
    if not d:
        return jsonify({'error': 'Introuvable'}), 404
    db.session.delete(d)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Dépense supprimée'})