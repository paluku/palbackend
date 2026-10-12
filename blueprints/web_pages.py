"""
Pages web HTML (Recettes, Marchandises, Stats).
Accès via session Flask-Login (navigateur) — PAS JWT.
"""
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash)
from flask_login import login_required, current_user

from extensions import db

from models import Recette, Marchandise
web_pages_bp = Blueprint('web_pages', __name__)


# Liste des jours en français
JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi',
         'Vendredi', 'Samedi', 'Dimanche']


def _jour_depuis_date(date_str):
    """Retourne le nom du jour ('Lundi', 'Mardi'...) depuis 'YYYY-MM-DD'."""
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        return JOURS[d.weekday()]   # weekday(): 0=Lundi, 6=Dimanche
    except ValueError:
        return None


# ==================================================
# RECETTES
# ==================================================
@web_pages_bp.route('/recettes', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def recettes():
    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        date_str = (request.form.get('date') or '').strip()
        heure = (request.form.get('heure') or '').strip()
        montant_str = (request.form.get('montant') or '').strip()
        devise = (request.form.get('devise') or 'CDF').strip()
        description = (request.form.get('description') or '').strip()

        erreurs = []

        if not nom:
            erreurs.append('Le nom est obligatoire')
        if not date_str:
            erreurs.append('La date est obligatoire')
        if not heure:
            erreurs.append("L'heure est obligatoire")

        # Calcul du jour
        jour = _jour_depuis_date(date_str) if date_str else None
        if date_str and not jour:
            erreurs.append('Format de date invalide')

        # Montant
        montant_val = None
        try:
            montant_val = float(montant_str)
            if montant_val <= 0:
                erreurs.append('Le montant doit être positif')
        except (ValueError, TypeError):
            erreurs.append('Montant invalide')

        if erreurs:
            for e in erreurs:
                flash(e, 'error')
        else:
            recette = Recette(
                user_id=current_user.id,
                nom=nom,
                jour=jour,
                date=date_str,
                heure=heure,
                montant=montant_val,
                devise=devise,
                description=description,
            )
            db.session.add(recette)
            db.session.commit()
            flash(f'Recette « {nom} » enregistrée ✅', 'success')
            return redirect(url_for('web_pages.recettes'))

    # GET : formulaire + liste
    mes_recettes = (Recette.query
                    .filter_by(user_id=current_user.id)
                    .order_by(Recette.date.desc(), Recette.id.desc())
                    .all())
    total = sum(r.montant for r in mes_recettes)

    return render_template(
        'recettes.html',
        recettes=mes_recettes,
        total=total,
        jours=JOURS,
    )


# ==================================================
# MARCHANDISES
# ==================================================
@web_pages_bp.route('/marchandises', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def marchandises():
    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        description = (request.form.get('description') or '').strip()
        prix_str = (request.form.get('prix_unitaire') or '').strip()
        qte_str = (request.form.get('quantite') or '').strip()
        red_str = (request.form.get('reduction_pct') or '0').strip()
        devise = (request.form.get('devise') or 'CDF').strip()

        erreurs = []

        if not nom:
            erreurs.append('Le nom est obligatoire')

        prix_val = None
        try:
            prix_val = float(prix_str)
            if prix_val <= 0:
                erreurs.append('Le prix doit être positif')
        except (ValueError, TypeError):
            erreurs.append('Prix unitaire invalide')

        qte_val = None
        try:
            qte_val = float(qte_str)
            if qte_val <= 0:
                erreurs.append('La quantité doit être positive')
        except (ValueError, TypeError):
            erreurs.append('Quantité invalide')

        red_val = 0.0
        try:
            red_val = float(red_str) if red_str else 0.0
            if red_val < 0 or red_val > 100:
                erreurs.append('La réduction doit être entre 0 et 100')
        except (ValueError, TypeError):
            erreurs.append('Réduction invalide')

        if erreurs:
            for e in erreurs:
                flash(e, 'error')
        else:
            m = Marchandise(
                user_id=current_user.id,
                nom=nom,
                description=description,
                prix_unitaire=prix_val,
                quantite=qte_val,
                reduction_pct=red_val,
                devise=devise,
            )
            db.session.add(m)
            db.session.commit()
            flash(f'Marchandise « {nom} » ajoutée ✅', 'success')
            return redirect(url_for('web_pages.marchandises'))

    # ----- GET : préparer les données pour le template -----
    mes_marchandises = (Marchandise.query
                        .filter_by(user_id=current_user.id)
                        .order_by(Marchandise.created_at.desc())
                        .all())

    total_brut = sum(m.prix_total_brut for m in mes_marchandises)
    total_net = sum(m.prix_total_net for m in mes_marchandises)
    total_red = total_brut - total_net

    return render_template(
        'marchandises.html',
        marchandises=mes_marchandises,
        total_brut=total_brut,
        total_net=total_net,
        total_red=total_red,
    )

# ==================================================
# STATS
# ==================================================

@web_pages_bp.route('/stats', strict_slashes=False)
@login_required
def stats():
    # --- RECETTES ---
    mes_recettes = (Recette.query
                    .filter_by(user_id=current_user.id)
                    .all())
    nb_recettes = len(mes_recettes)
    total_recettes = sum(r.montant for r in mes_recettes)

    # Totaux par devise
    recettes_par_devise = {}
    for r in mes_recettes:
        recettes_par_devise[r.devise] = recettes_par_devise.get(r.devise, 0) + r.montant

    # --- MARCHANDISES ---
    mes_marchandises = (Marchandise.query
                        .filter_by(user_id=current_user.id)
                        .all())
    nb_marchandises = len(mes_marchandises)
    total_brut = sum(m.prix_total_brut for m in mes_marchandises)
    total_net = sum(m.prix_total_net for m in mes_marchandises)
    total_reductions = total_brut - total_net

    # Marchandises par devise
    marchandises_par_devise = {}
    for m in mes_marchandises:
        marchandises_par_devise[m.devise] = (
            marchandises_par_devise.get(m.devise, 0) + m.prix_total_net
        )

    return render_template(
        'stats.html',
        nb_recettes=nb_recettes,
        total_recettes=total_recettes,
        recettes_par_devise=recettes_par_devise,
        nb_marchandises=nb_marchandises,
        total_brut=total_brut,
        total_net=total_net,
        total_reductions=total_reductions,
        marchandises_par_devise=marchandises_par_devise,
    )
    
# ==================================================
# ADMIN — données pour le dashboard
# ==================================================
def _is_admin():
    return current_user.is_authenticated and getattr(current_user, 'is_admin', False)


@web_pages_bp.context_processor
def injecter_donnees_admin():
    """Fournit des données admin au template admin/dashboard.html."""
    from flask import request
    if not _is_admin():
        return {}
    if not request.path.startswith('/admin'):
        return {}

    from models import User

    users = User.query.order_by(User.created_at.desc()).all()
    recettes = Recette.query.order_by(Recette.created_at.desc()).all()
    marchandises = Marchandise.query.order_by(Marchandise.created_at.desc()).all()

    total_recettes = sum(r.montant for r in recettes)
    total_brut = sum(m.prix_total_brut for m in marchandises)
    total_net = sum(m.prix_total_net for m in marchandises)
    total_red = total_brut - total_net

    return {
        'admin_users': users,
        'admin_recettes': recettes,
        'admin_marchandises': marchandises,
        'admin_total_recettes': total_recettes,
        'admin_total_brut': total_brut,
        'admin_total_net': total_net,
        'admin_total_red': total_red,
    }


# ==================================================
# ADMIN — actions
# ==================================================
@web_pages_bp.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
def admin_change_role(user_id):
    if not _is_admin():
        flash("Accès réservé à l'administrateur.", 'error')
        return redirect(url_for('pages.home'))
    from models import User
    user = db.session.get(User, user_id)
    if not user:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('pages.admin'))
    if user.id == current_user.id:
        flash('Vous ne pouvez pas changer votre propre rôle.', 'warning')
        return redirect(url_for('pages.admin'))

    new_role = (request.form.get('role') or '').strip().lower()
    if new_role not in ('user', 'admin'):
        flash('Rôle invalide.', 'error')
        return redirect(url_for('pages.admin'))

    user.role = new_role
    db.session.commit()
    flash(f'Rôle de « {user.nom} » changé en {new_role}.', 'success')
    return redirect(url_for('pages.admin'))


@web_pages_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not _is_admin():
        flash("Accès réservé à l'administrateur.", 'error')
        return redirect(url_for('pages.home'))
    from models import User
    user = db.session.get(User, user_id)
    if not user:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('pages.admin'))
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'warning')
        return redirect(url_for('pages.admin'))

    nom = user.nom
    # Supprime aussi ses données
    Recette.query.filter_by(user_id=user_id).delete()
    Marchandise.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f'Utilisateur « {nom} » supprimé.', 'success')
    return redirect(url_for('pages.admin'))


@web_pages_bp.route('/admin/recettes/<int:recette_id>/delete', methods=['POST'])
@login_required
def admin_delete_recette(recette_id):
    if not _is_admin():
        flash("Accès réservé à l'administrateur.", 'error')
        return redirect(url_for('pages.home'))
    r = db.session.get(Recette, recette_id)
    if not r:
        flash('Recette introuvable.', 'error')
        return redirect(url_for('pages.admin'))
    nom = r.nom
    db.session.delete(r)
    db.session.commit()
    flash(f'Recette « {nom} » supprimée.', 'success')
    return redirect(url_for('pages.admin'))


@web_pages_bp.route('/admin/marchandises/<int:m_id>/delete', methods=['POST'])
@login_required
def admin_delete_marchandise(m_id):
    if not _is_admin():
        flash("Accès réservé à l'administrateur.", 'error')
        return redirect(url_for('pages.home'))
    m = db.session.get(Marchandise, m_id)
    if not m:
        flash('Marchandise introuvable.', 'error')
        return redirect(url_for('pages.admin'))
    nom = m.nom
    db.session.delete(m)
    db.session.commit()
    flash(f'Marchandise « {nom} » supprimée.', 'success')
    return redirect(url_for('pages.admin'))