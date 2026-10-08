"""
API Marchandises.
- GET    /api/marchandises         → liste
- POST   /api/marchandises         → créer
- PUT    /api/marchandises/<id>    → modifier
- DELETE /api/marchandises/<id>    → supprimer (⚠️ admin)
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from extensions import db
from models import Marchandise
from logs_utils import log_action

api_marchandises_bp = Blueprint('api_marchandises', __name__, url_prefix='/api/marchandises')


@api_marchandises_bp.route('', methods=['GET'], strict_slashes=False)
@jwt_required()
def liste():
    devise = request.args.get('devise')

    query = Marchandise.query.filter_by(user_id=current_user.id)
    if devise:
        query = query.filter(Marchandise.devise == devise)

    items = query.order_by(Marchandise.created_at.desc()).all()

    return jsonify({
        'success': True,
        'total': len(items),
        'marchandises': [m.to_dict() for m in items],
    })


@api_marchandises_bp.route('', methods=['POST'], strict_slashes=False)
@jwt_required()
def creer():
    data = request.json or {}
    nom = (data.get('nom') or '').strip()
    description = (data.get('description') or '').strip()
    devise = (data.get('devise') or 'CDF').upper()

    try:
        prix = float(data.get('prix_unitaire', 0))
        qte = float(data.get('quantite', 1))
        reduction = float(data.get('reduction_pct', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Valeurs numériques invalides'}), 400

    if not nom:
        return jsonify({'error': 'Nom obligatoire'}), 400
    if prix <= 0:
        return jsonify({'error': 'Prix > 0 obligatoire'}), 400
    if qte <= 0:
        return jsonify({'error': 'Quantité > 0 obligatoire'}), 400
    if reduction < 0 or reduction > 100:
        return jsonify({'error': 'Réduction entre 0 et 100'}), 400
    if devise not in ('CDF', 'EUR', 'USD'):
        return jsonify({'error': 'Devise invalide'}), 400

    m = Marchandise(
        user_id=current_user.id,
        nom=nom,
        description=description,
        prix_unitaire=prix,
        quantite=qte,
        reduction_pct=reduction,
        devise=devise,
    )
    db.session.add(m)
    db.session.commit()

    log_action('marchandise_created', f'{nom} x{qte}', user=current_user)

    return jsonify({
        'success': True,
        'message': 'Marchandise ajoutée',
        'marchandise': m.to_dict(),
    }), 201


@api_marchandises_bp.route('/<int:mid>', methods=['PUT'], strict_slashes=False)
@jwt_required()
def modifier(mid):
    m = Marchandise.query.filter_by(id=mid, user_id=current_user.id).first()
    if not m:
        return jsonify({'error': 'Marchandise introuvable'}), 404

    data = request.json or {}

    if 'nom' in data:
        m.nom = (data['nom'] or '').strip()
    if 'description' in data:
        m.description = (data['description'] or '').strip()
    if 'prix_unitaire' in data:
        try:
            p = float(data['prix_unitaire'])
            if p > 0:
                m.prix_unitaire = p
        except (TypeError, ValueError):
            pass
    if 'quantite' in data:
        try:
            q = float(data['quantite'])
            if q > 0:
                m.quantite = q
        except (TypeError, ValueError):
            pass
    if 'reduction_pct' in data:
        try:
            r = float(data['reduction_pct'])
            if 0 <= r <= 100:
                m.reduction_pct = r
        except (TypeError, ValueError):
            pass
    if 'devise' in data:
        d = (data['devise'] or '').upper()
        if d in ('CDF', 'EUR', 'USD'):
            m.devise = d

    db.session.commit()
    log_action('marchandise_updated', f'ID {mid}', user=current_user)

    return jsonify({
        'success': True,
        'message': 'Marchandise modifiée',
        'marchandise': m.to_dict(),
    })


@api_marchandises_bp.route('/<int:mid>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def supprimer(mid):
    if not current_user.is_admin:
        return jsonify({
            'error': 'Suppression réservée à l\'administrateur',
            'need_admin': True,
        }), 403

    m = Marchandise.query.filter_by(id=mid, user_id=current_user.id).first()
    if not m:
        return jsonify({'error': 'Marchandise introuvable'}), 404

    db.session.delete(m)
    db.session.commit()
    log_action('marchandise_deleted', f'ID {mid}', user=current_user)

    return jsonify({'success': True, 'message': 'Marchandise supprimée'})