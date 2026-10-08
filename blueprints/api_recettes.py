"""
API Recettes journalières.
- GET    /api/recettes          → liste (filtre par mois, jour, devise)
- POST   /api/recettes          → créer
- GET    /api/recettes/<id>     → détail
- PUT    /api/recettes/<id>     → modifier (✅ auth requise)
- DELETE /api/recettes/<id>     → supprimer (⚠️ admin uniquement)
- GET    /api/recettes/totaux   → totaux par devise
"""
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from extensions import db
from models import Recette
from logs_utils import log_action

api_recettes_bp = Blueprint('api_recettes', __name__, url_prefix='/api/recettes')


# ==================== LISTE ====================
@api_recettes_bp.route('', methods=['GET'], strict_slashes=False)
@jwt_required()
def liste():
    query = Recette.query.filter_by(user_id=current_user.id)

    mois = request.args.get('mois')     # format: YYYY-MM
    jour = request.args.get('jour')     # Lundi, Mardi...
    date_exacte = request.args.get('date')  # YYYY-MM-DD
    devise = request.args.get('devise')

    if mois:
        query = query.filter(Recette.date.like(f'{mois}-%'))
    if jour:
        query = query.filter(Recette.jour == jour)
    if date_exacte:
        query = query.filter(Recette.date == date_exacte)
    if devise:
        query = query.filter(Recette.devise == devise)

    recettes = query.order_by(Recette.date.desc(), Recette.heure.desc()).all()

    return jsonify({
        'success': True,
        'total': len(recettes),
        'recettes': [r.to_dict() for r in recettes],
    })


# ==================== CRÉER ====================
@api_recettes_bp.route('', methods=['POST'], strict_slashes=False)
@jwt_required()
def creer():
    data = request.json or {}
    nom = (data.get('nom') or '').strip()
    jour = (data.get('jour') or '').strip()
    date = (data.get('date') or '').strip()
    heure = (data.get('heure') or '').strip()
    montant = data.get('montant')
    devise = (data.get('devise') or 'CDF').upper()
    description = (data.get('description') or '').strip()

    # Validation
    if not all([nom, jour, date, heure]):
        return jsonify({'error': 'Champs obligatoires : nom, jour, date, heure'}), 400

    if devise not in ('CDF', 'EUR', 'USD'):
        return jsonify({'error': 'Devise invalide (CDF, EUR, USD)'}), 400

    try:
        montant = float(montant)
    except (TypeError, ValueError):
        return jsonify({'error': 'Montant invalide'}), 400

    if montant <= 0:
        return jsonify({'error': 'Montant doit être > 0'}), 400

    recette = Recette(
        user_id=current_user.id,
        nom=nom,
        jour=jour,
        date=date,
        heure=heure,
        montant=montant,
        devise=devise,
        description=description,
    )
    db.session.add(recette)
    db.session.commit()

    log_action('recette_created', f'{nom} — {montant} {devise}', user=current_user)

    return jsonify({
        'success': True,
        'message': 'Recette ajoutée',
        'recette': recette.to_dict(),
    }), 201


# ==================== DÉTAIL ====================
@api_recettes_bp.route('/<int:rid>', methods=['GET'], strict_slashes=False)
@jwt_required()
def detail(rid):
    r = Recette.query.filter_by(id=rid, user_id=current_user.id).first()
    if not r:
        return jsonify({'error': 'Recette introuvable'}), 404
    return jsonify({'success': True, 'recette': r.to_dict()})


# ==================== MODIFIER ====================
@api_recettes_bp.route('/<int:rid>', methods=['PUT'], strict_slashes=False)
@jwt_required()
def modifier(rid):
    r = Recette.query.filter_by(id=rid, user_id=current_user.id).first()
    if not r:
        return jsonify({'error': 'Recette introuvable'}), 404

    data = request.json or {}

    if 'nom' in data:
        r.nom = (data['nom'] or '').strip()
    if 'jour' in data:
        r.jour = (data['jour'] or '').strip()
    if 'date' in data:
        r.date = (data['date'] or '').strip()
    if 'heure' in data:
        r.heure = (data['heure'] or '').strip()
    if 'montant' in data:
        try:
            m = float(data['montant'])
            if m > 0:
                r.montant = m
        except (TypeError, ValueError):
            pass
    if 'devise' in data:
        d = (data['devise'] or '').upper()
        if d in ('CDF', 'EUR', 'USD'):
            r.devise = d
    if 'description' in data:
        r.description = (data['description'] or '').strip()

    db.session.commit()
    log_action('recette_updated', f'ID {rid}', user=current_user)

    return jsonify({
        'success': True,
        'message': 'Recette modifiée',
        'recette': r.to_dict(),
    })


# ==================== SUPPRIMER (⚠️ ADMIN UNIQUEMENT) ====================
@api_recettes_bp.route('/<int:rid>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def supprimer(rid):
    if not current_user.is_admin:
        return jsonify({
            'error': 'Suppression réservée à l\'administrateur',
            'need_admin': True,
        }), 403

    r = Recette.query.filter_by(id=rid, user_id=current_user.id).first()
    if not r:
        return jsonify({'error': 'Recette introuvable'}), 404

    db.session.delete(r)
    db.session.commit()
    log_action('recette_deleted', f'ID {rid}', user=current_user)

    return jsonify({'success': True, 'message': 'Recette supprimée'})


# ==================== TOTAUX ====================
@api_recettes_bp.route('/totaux', methods=['GET'], strict_slashes=False)
@jwt_required()
def totaux():
    mois = request.args.get('mois')  # YYYY-MM

    query = Recette.query.filter_by(user_id=current_user.id)
    if mois:
        query = query.filter(Recette.date.like(f'{mois}-%'))

    recettes = query.all()

    result = {'CDF': 0, 'EUR': 0, 'USD': 0}
    for r in recettes:
        result[r.devise] = result.get(r.devise, 0) + r.montant

    return jsonify({
        'success': True,
        'totaux': result,
        'nb_recettes': len(recettes),
    })