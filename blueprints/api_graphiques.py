"""API JSON pour les graphiques (courbe recettes, camembert marchandises)."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from extensions import db
from models import Recette, Marchandise

api_graphiques_bp = Blueprint('api_graphiques', __name__, url_prefix='/api/graphiques')


@api_graphiques_bp.route('', methods=['GET'], strict_slashes=False)
@jwt_required()
def graphiques_data():
    # --- Courbe : recettes par date ---
    recettes = Recette.query.order_by(Recette.date.asc()).all()
    recettes_par_date = {}
    for r in recettes:
        recettes_par_date[r.date] = recettes_par_date.get(r.date, 0) + r.montant

    dates = sorted(recettes_par_date.keys())
    montants = [round(recettes_par_date[d], 2) for d in dates]

    # --- Camembert : marchandises par devise (net) ---
    marchandises = Marchandise.query.all()
    marchandises_par_devise = {}
    for m in marchandises:
        marchandises_par_devise[m.devise] = (
            marchandises_par_devise.get(m.devise, 0) + m.prix_total_net
        )

    # --- KPI globaux ---
    total_recettes = sum(r.montant for r in recettes)
    total_marchandises = sum(m.prix_total_net for m in marchandises)
    total_global = total_recettes + total_marchandises

    return jsonify({
        'success': True,
        'courbe': {
            'dates': dates,
            'montants': montants,
        },
        'camembert': {
            'labels': list(marchandises_par_devise.keys()),
            'values': [round(v, 2) for v in marchandises_par_devise.values()],
        },
        'kpi': {
            'total_recettes': round(total_recettes, 2),
            'total_marchandises': round(total_marchandises, 2),
            'total_global': round(total_global, 2),
        },
    })