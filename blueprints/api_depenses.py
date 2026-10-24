"""
API JSON pour les dépenses — Flutter + React.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from extensions import db
from models import Depense
from logs_utils import log_action

api_depenses_bp = Blueprint('api_depenses', __name__, url_prefix='/api/depenses')


def _is_admin():
    return getattr(current_user, 'is_admin', False)


@api_depenses_bp.route('/ping', methods=['GET'], strict_slashes=False)
def ping():
    return jsonify({'success': True, 'module': 'depenses'})


@api_depenses_bp.route('', methods=['GET'], strict_slashes=False)
@jwt_required()
def list_depenses():
    depenses = (Depense.query
                .order_by(Depense.date.desc(), Depense.id.desc())
                .all())
    total = sum(d.montant for d in depenses)
    return jsonify({
        'success': True,
        'count': len(depenses),
        'total': round(total, 2),
        'depenses': [d.to_dict() for d in depenses],
    })


@api_depenses_bp.route('', methods=['POST'], strict_slashes=False)
@jwt_required()
def create_depense():
    data = request.get_json(silent=True) or {}
    nom = (data.get('nom') or '').strip()
    categorie = (data.get('categorie') or 'Autre').strip()
    date_str = (data.get('date') or '').strip()
    heure = (data.get('heure') or '').strip()
    devise = (data.get('devise') or 'CDF').strip()
    description = (data.get('description') or '').strip()

    erreurs = []
    if not nom: erreurs.append('Le nom est obligatoire')
    if not date_str: erreurs.append('La date est obligatoire')
    if not heure: erreurs.append("L'heure est obligatoire")

    montant_val = None
    try:
        montant_val = float(data.get('montant', 0))
        if montant_val < 0:
            erreurs.append('Le montant ne peut pas être négatif')
    except (ValueError, TypeError):
        erreurs.append('Montant invalide')

    if erreurs:
        return jsonify({'error': ' | '.join(erreurs)}), 400

    d = Depense(
        user_id=current_user.id,
        nom=nom, categorie=categorie,
        date=date_str, heure=heure,
        montant=montant_val, devise=devise,
        description=description,
    )
    db.session.add(d)
    db.session.commit()
    log_action('api_depense_created', f'{nom} ({montant_val} {devise})', user=current_user)
    return jsonify({
        'success': True,
        'message': f'Dépense « {nom} » enregistrée',
        'depense': d.to_dict(),
    }), 201


@api_depenses_bp.route('/<int:depense_id>', methods=['PUT'], strict_slashes=False)
@jwt_required()
def update_depense(depense_id):
    d = db.session.get(Depense, depense_id)
    if not d:
        return jsonify({'error': 'Dépense introuvable'}), 404
    if d.user_id != current_user.id and not _is_admin():
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json(silent=True) or {}
    nom = (data.get('nom') or '').strip()
    categorie = (data.get('categorie') or 'Autre').strip()
    date_str = (data.get('date') or '').strip()
    heure = (data.get('heure') or '').strip()
    devise = (data.get('devise') or 'CDF').strip()
    description = (data.get('description') or '').strip()

    erreurs = []
    if not nom: erreurs.append('Le nom est obligatoire')
    if not date_str: erreurs.append('La date est obligatoire')
    if not heure: erreurs.append("L'heure est obligatoire")

    try:
        montant_val = float(data.get('montant', 0))
        if montant_val < 0:
            erreurs.append('Le montant ne peut pas être négatif')
    except (ValueError, TypeError):
        erreurs.append('Montant invalide')
        montant_val = None

    if erreurs:
        return jsonify({'error': ' | '.join(erreurs)}), 400

    d.nom = nom
    d.categorie = categorie
    d.date = date_str
    d.heure = heure
    d.montant = montant_val
    d.devise = devise
    d.description = description
    db.session.commit()
    log_action('api_depense_updated', f'{nom}', user=current_user)

    return jsonify({
        'success': True,
        'message': f'Dépense « {nom} » modifiée',
        'depense': d.to_dict(),
    })


@api_depenses_bp.route('/<int:depense_id>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def delete_depense(depense_id):
    d = db.session.get(Depense, depense_id)
    if not d:
        return jsonify({'error': 'Dépense introuvable'}), 404
    if d.user_id != current_user.id and not _is_admin():
        return jsonify({'error': 'Non autorisé'}), 403
    nom = d.nom
    db.session.delete(d)
    db.session.commit()
    log_action('api_depense_deleted', f'{nom}', user=current_user)
    return jsonify({'success': True, 'message': f'Dépense « {nom} » supprimée'})