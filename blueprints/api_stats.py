"""
API Statistiques + Graphiques.
- GET /api/stats/dashboard       → résumé global
- GET /api/stats/caisse          → recettes par jour (7 derniers jours)
- GET /api/stats/marchandises    → top marchandises vendues
- GET /api/stats/par-mois        → recettes par mois
"""
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy import func

from extensions import db
from models import Recette, Marchandise

api_stats_bp = Blueprint('api_stats', __name__, url_prefix='/api/stats')


# ==================== DASHBOARD ====================
@api_stats_bp.route('/dashboard', methods=['GET'], strict_slashes=False)
@jwt_required()
def dashboard():
    # Recettes totales
    recettes = Recette.query.filter_by(user_id=current_user.id).all()

    total_par_devise = {'CDF': 0, 'EUR': 0, 'USD': 0}
    for r in recettes:
        total_par_devise[r.devise] = total_par_devise.get(r.devise, 0) + r.montant

    # Marchandises
    marchandises = Marchandise.query.filter_by(user_id=current_user.id).all()

    total_marchandises = 0
    for m in marchandises:
        total_marchandises += m.prix_total_net

    # Recettes aujourd'hui
    today = datetime.now().strftime('%Y-%m-%d')
    recettes_today = [r for r in recettes if r.date == today]

    return jsonify({
        'success': True,
        'total_caisse': total_par_devise,
        'total_marchandises': round(total_marchandises, 2),
        'nb_recettes': len(recettes),
        'nb_marchandises': len(marchandises),
        'recettes_aujourd_hui': len(recettes_today),
    })


# ==================== GRAPHIQUE CAISSE ====================
@api_stats_bp.route('/caisse', methods=['GET'], strict_slashes=False)
@jwt_required()
def graphique_caisse():
    devise = request.args.get('devise', 'CDF')
    jours = int(request.args.get('jours', 7))

    aujourd_hui = datetime.now().date()
    result = []

    for i in range(jours - 1, -1, -1):
        jour = aujourd_hui - timedelta(days=i)
        date_str = jour.strftime('%Y-%m-%d')

        recettes_jour = Recette.query.filter_by(
            user_id=current_user.id,
            date=date_str,
            devise=devise,
        ).all()

        total = sum(r.montant for r in recettes_jour)

        result.append({
            'date': date_str,
            'label': jour.strftime('%d/%m'),
            'jour': jour.strftime('%A'),
            'montant': round(total, 2),
        })

    return jsonify({
        'success': True,
        'devise': devise,
        'data': result,
    })


# ==================== TOP MARCHANDISES ====================
@api_stats_bp.route('/marchandises', methods=['GET'], strict_slashes=False)
@jwt_required()
def graphique_marchandises():
    devise = request.args.get('devise', 'CDF')
    limite = int(request.args.get('limite', 10))

    marchandises = Marchandise.query.filter_by(
        user_id=current_user.id,
        devise=devise,
    ).all()

    # Trier par prix total net
    marchandises_sorted = sorted(
        marchandises,
        key=lambda m: m.prix_total_net,
        reverse=True,
    )[:limite]

    result = [
        {
            'nom': m.nom,
            'prix_total': round(m.prix_total_net, 2),
            'quantite': m.quantite,
        }
        for m in marchandises_sorted
    ]

    return jsonify({
        'success': True,
        'devise': devise,
        'data': result,
    })


# ==================== RECETTES PAR MOIS ====================
@api_stats_bp.route('/par-mois', methods=['GET'], strict_slashes=False)
@jwt_required()
def recettes_par_mois():
    devise = request.args.get('devise', 'CDF')

    recettes = Recette.query.filter_by(
        user_id=current_user.id,
        devise=devise,
    ).all()

    par_mois = defaultdict(float)
    for r in recettes:
        mois = r.date[:7]  # YYYY-MM
        par_mois[mois] += r.montant

    # Trier chronologiquement
    data = []
    for mois in sorted(par_mois.keys()):
        annee, m = mois.split('-')
        label = f"{m}/{annee}"
        data.append({
            'mois': mois,
            'label': label,
            'montant': round(par_mois[mois], 2),
        })

    return jsonify({
        'success': True,
        'devise': devise,
        'data': data,
    })


# ==================== BONUS : RÉSUMÉ COMPLET ====================
@api_stats_bp.route('/resume-complet', methods=['GET'], strict_slashes=False)
@jwt_required()
def resume_complet():
    """Résumé complet avec tous les totaux."""
    devise = request.args.get('devise', 'CDF')

    recettes = Recette.query.filter_by(
        user_id=current_user.id,
        devise=devise,
    ).all()

    marchandises = Marchandise.query.filter_by(
        user_id=current_user.id,
        devise=devise,
    ).all()

    total_recettes = sum(r.montant for r in recettes)
    total_marchandises_net = sum(m.prix_total_net for m in marchandises)
    total_reductions = sum(m.montant_reduction for m in marchandises)

    return jsonify({
        'success': True,
        'devise': devise,
        'caisse': {
            'recettes': round(total_recettes, 2),
            'depenses': round(total_marchandises_net, 2),
            'solde': round(total_recettes - total_marchandises_net, 2),
        },
        'marchandises': {
            'nb': len(marchandises),
            'total_brut': round(sum(m.prix_total_brut for m in marchandises), 2),
            'reductions': round(total_reductions, 2),
            'total_net': round(total_marchandises_net, 2),
        },
        'recettes': {
            'nb': len(recettes),
            'total': round(total_recettes, 2),
        },
    })