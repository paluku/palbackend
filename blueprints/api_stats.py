"""API JSON statistiques globales."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, current_user

from extensions import db
from models import Recette, Depense, Marchandise

api_stats_bp = Blueprint('api_stats', __name__, url_prefix='/api/stats')


@api_stats_bp.route('/ping', methods=['GET'], strict_slashes=False)
def ping():
    return jsonify({'success': True, 'module': 'stats'})


@api_stats_bp.route('', methods=['GET'], strict_slashes=False)
@jwt_required()
def stats_global():
    # Recettes
    recettes = Recette.query.all()
    total_recettes = sum(r.montant for r in recettes)
    recettes_par_devise = {}
    for r in recettes:
        recettes_par_devise[r.devise] = recettes_par_devise.get(r.devise, 0) + r.montant

    # Dépenses
    depenses = Depense.query.all()
    total_depenses = sum(d.montant for d in depenses)
    depenses_par_devise = {}
    for d in depenses:
        depenses_par_devise[d.devise] = depenses_par_devise.get(d.devise, 0) + d.montant

    # Marchandises
    marchandises = Marchandise.query.all()
    total_brut = sum(m.prix_total_brut for m in marchandises)
    total_net = sum(m.prix_total_net for m in marchandises)
    total_red = total_brut - total_net
    marchandises_par_devise = {}
    for m in marchandises:
        marchandises_par_devise[m.devise] = (
            marchandises_par_devise.get(m.devise, 0) + m.prix_total_net
        )

    # Solde par devise
    devises = set(recettes_par_devise) | set(depenses_par_devise)
    solde_par_devise = {
        dv: recettes_par_devise.get(dv, 0) - depenses_par_devise.get(dv, 0)
        for dv in devises
    }

    return jsonify({
        'success': True,
        'recettes': {
            'count': len(recettes),
            'total': round(total_recettes, 2),
            'par_devise': {k: round(v, 2) for k, v in recettes_par_devise.items()},
        },
        'depenses': {
            'count': len(depenses),
            'total': round(total_depenses, 2),
            'par_devise': {k: round(v, 2) for k, v in depenses_par_devise.items()},
        },
        'marchandises': {
            'count': len(marchandises),
            'total_brut': round(total_brut, 2),
            'total_net': round(total_net, 2),
            'total_reductions': round(total_red, 2),
            'par_devise': {k: round(v, 2) for k, v in marchandises_par_devise.items()},
        },
        'solde_par_devise': {k: round(v, 2) for k, v in solde_par_devise.items()},
        'solde_global': round(total_recettes - total_depenses, 2),
    })