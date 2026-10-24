"""
API JSON pour les recettes — utilisée par Flutter + React.
Authentification : JWT (Authorization: Bearer <token>)
"""
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from extensions import db
from models import Recette
from logs_utils import log_action

api_recettes_bp = Blueprint('api_recettes', __name__, url_prefix='/api/recettes')

JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi',
         'Vendredi', 'Samedi', 'Dimanche']


def _jour_depuis_date(date_str):
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        return JOURS[d.weekday()]
    except (ValueError, TypeError):
        return None


def _is_admin():
    return getattr(current_user, 'is_admin', False)


# ==================================================
# PING
# ==================================================
@api_recettes_bp.route('/ping', methods=['GET'], strict_slashes=False)
def ping():
    return jsonify({'success': True, 'module': 'recettes'})


# ==================================================
# LISTER TOUTES LES RECETTES (partagées)
# ==================================================
@api_recettes_bp.route('', methods=['GET'], strict_slashes=False)
@jwt_required()
def list_recettes():
    recettes = (Recette.query
                .order_by(Recette.date.desc(), Recette.id.desc())
                .all())

    total = sum(r.montant for r in recettes)

    return jsonify({
        'success': True,
        'count': len(recettes),
        'total': round(total, 2),
        'recettes': [r.to_dict() for r in recettes],
    })


# ==================================================
# AJOUTER UNE RECETTE
# ==================================================
@api_recettes_bp.route('', methods=['POST'], strict_slashes=False)
@jwt_required()
def create_recette():
    data = request.get_json(silent=True) or {}

    nom = (data.get('nom') or '').strip()
    date_str = (data.get('date') or '').strip()
    heure = (data.get('heure') or '').strip()
    devise = (data.get('devise') or 'CDF').strip()
    description = (data.get('description') or '').strip()

    erreurs = []
    if not nom:
        erreurs.append('Le nom est obligatoire')
    if not date_str:
        erreurs.append('La date est obligatoire')
    if not heure:
        erreurs.append("L'heure est obligatoire")

    jour = _jour_depuis_date(date_str) if date_str else None
    if date_str and not jour:
        erreurs.append('Format de date invalide (YYYY-MM-DD)')

    montant_val = None
    try:
        montant_val = float(data.get('montant', 0))
        if montant_val < 0:
            erreurs.append('Le montant ne peut pas être négatif')
    except (ValueError, TypeError):
        erreurs.append('Montant invalide')

    if erreurs:
        return jsonify({'error': ' | '.join(erreurs)}), 400

    recette = Recette(
        user_id=current_user.id,
        nom=nom, jour=jour, date=date_str, heure=heure,
        montant=montant_val, devise=devise,
        description=description,
    )
    db.session.add(recette)
    db.session.commit()

    log_action('api_recette_created', f'{nom} ({montant_val} {devise})',
               user=current_user)

    return jsonify({
        'success': True,
        'message': f'Recette « {nom} » enregistrée',
        'recette': recette.to_dict(),
    }), 201


# ==================================================
# MODIFIER UNE RECETTE
# ==================================================
@api_recettes_bp.route('/<int:recette_id>', methods=['PUT'], strict_slashes=False)
@jwt_required()
def update_recette(recette_id):
    r = db.session.get(Recette, recette_id)
    if not r:
        return jsonify({'error': 'Recette introuvable'}), 404

    if r.user_id != current_user.id and not _is_admin():
        return jsonify({'error': 'Non autorisé à modifier cette recette'}), 403

    data = request.get_json(silent=True) or {}

    nom = (data.get('nom') or '').strip()
    date_str = (data.get('date') or '').strip()
    heure = (data.get('heure') or '').strip()
    devise = (data.get('devise') or 'CDF').strip()
    description = (data.get('description') or '').strip()

    erreurs = []
    if not nom:
        erreurs.append('Le nom est obligatoire')
    if not date_str:
        erreurs.append('La date est obligatoire')
    if not heure:
        erreurs.append("L'heure est obligatoire")

    jour = _jour_depuis_date(date_str) if date_str else None
    if date_str and not jour:
        erreurs.append('Format de date invalide')

    try:
        montant_val = float(data.get('montant', 0))
        if montant_val < 0:
            erreurs.append('Le montant ne peut pas être négatif')
    except (ValueError, TypeError):
        erreurs.append('Montant invalide')
        montant_val = None

    if erreurs:
        return jsonify({'error': ' | '.join(erreurs)}), 400

    r.nom = nom
    r.jour = jour
    r.date = date_str
    r.heure = heure
    r.montant = montant_val
    r.devise = devise
    r.description = description
    db.session.commit()

    log_action('api_recette_updated', f'{nom}', user=current_user)

    return jsonify({
        'success': True,
        'message': f'Recette « {nom} » modifiée',
        'recette': r.to_dict(),
    })


# ==================================================
# SUPPRIMER UNE RECETTE
# ==================================================
@api_recettes_bp.route('/<int:recette_id>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def delete_recette(recette_id):
    r = db.session.get(Recette, recette_id)
    if not r:
        return jsonify({'error': 'Recette introuvable'}), 404

    if r.user_id != current_user.id and not _is_admin():
        return jsonify({'error': 'Non autorisé à supprimer cette recette'}), 403

    nom = r.nom
    db.session.delete(r)
    db.session.commit()

    log_action('api_recette_deleted', f'{nom}', user=current_user)

    return jsonify({
        'success': True,
        'message': f'Recette « {nom} » supprimée',
    })