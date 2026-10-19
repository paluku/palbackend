"""
Pages web HTML (Recettes, Dépenses, Marchandises, Stats, Admin, Export CSV).
Accès via session Flask-Login (navigateur) — PAS JWT.

⚠️ MODE PARTAGÉ : tous les utilisateurs connectés voient TOUTES les données.
   Seul le créateur (ou l'admin) peut modifier/supprimer sa propre entrée.
"""
import csv
import io
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, Response)
from flask_login import login_required, current_user

from extensions import db
from models import Recette, Marchandise, Depense

web_pages_bp = Blueprint('web_pages', __name__)

JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi',
         'Vendredi', 'Samedi', 'Dimanche']

CATEGORIES_DEPENSES = [
    'Alimentation', 'Transport', 'Loyer', 'Salaires',
    'Électricité', 'Eau', 'Internet', 'Fournitures',
    'Santé', 'Éducation', 'Autre',
]


def _jour_depuis_date(date_str):
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        return JOURS[d.weekday()]
    except ValueError:
        return None


def _is_admin():
    return current_user.is_authenticated and getattr(current_user, 'is_admin', False)


def _total_recettes():
    """Total global (tous utilisateurs)."""
    return (db.session.query(db.func.coalesce(db.func.sum(Recette.montant), 0))
            .scalar() or 0)


def _total_depenses():
    """Total global (tous utilisateurs)."""
    return (db.session.query(db.func.coalesce(db.func.sum(Depense.montant), 0))
            .scalar() or 0)


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

        jour = _jour_depuis_date(date_str) if date_str else None
        if date_str and not jour:
            erreurs.append('Format de date invalide')

        montant_val = None
        try:
            montant_val = float(montant_str)
            if montant_val < 0:
                erreurs.append('Le montant doit être positif')
        except (ValueError, TypeError):
            erreurs.append('Montant invalide')

        if erreurs:
            for e in erreurs:
                flash(e, 'error')
        else:
            recette = Recette(
                user_id=current_user.id,
                nom=nom, jour=jour, date=date_str, heure=heure,
                montant=montant_val, devise=devise,
                description=description,
            )
            db.session.add(recette)
            db.session.commit()
            flash(f'Recette « {nom} » enregistrée ✅', 'success')
            return redirect(url_for('web_pages.recettes'))

    # ✅ PARTAGÉ : toutes les recettes de tout le monde
    mes_recettes = (Recette.query
                    .order_by(Recette.date.desc(), Recette.id.desc())
                    .all())
    total = sum(r.montant for r in mes_recettes)
    total_depenses = _total_depenses()
    solde_net = total - total_depenses

    return render_template(
        'recettes.html',
        recettes=mes_recettes,
        total=total,
        total_depenses=total_depenses,
        solde_net=solde_net,
        jours=JOURS,
    )


@web_pages_bp.route('/recettes/<int:recette_id>/edit', methods=['POST'])
@login_required
def recette_edit(recette_id):
    r = db.session.get(Recette, recette_id)
    if not r:
        flash('Recette introuvable.', 'error')
        return redirect(url_for('web_pages.recettes'))
    if r.user_id != current_user.id and not _is_admin():
        flash('Vous ne pouvez modifier que vos propres recettes.', 'warning')
        return redirect(url_for('web_pages.recettes'))

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

    jour = _jour_depuis_date(date_str) if date_str else None
    if date_str and not jour:
        erreurs.append('Format de date invalide')

    try:
        montant_val = float(montant_str)
        if montant_val <= 0:
            erreurs.append('Le montant doit être positif')
    except (ValueError, TypeError):
        erreurs.append('Montant invalide')
        montant_val = None

    if erreurs:
        for e in erreurs:
            flash(e, 'error')
    else:
        r.nom = nom
        r.jour = jour
        r.date = date_str
        r.heure = heure
        r.montant = montant_val
        r.devise = devise
        r.description = description
        db.session.commit()
        flash(f'Recette « {nom} » modifiée ✅', 'success')

    return redirect(url_for('web_pages.recettes'))


@web_pages_bp.route('/recettes/<int:recette_id>/delete', methods=['POST'])
@login_required
def recette_delete(recette_id):
    r = db.session.get(Recette, recette_id)
    if not r:
        flash('Recette introuvable.', 'error')
        return redirect(url_for('web_pages.recettes'))
    if r.user_id != current_user.id and not _is_admin():
        flash('Vous ne pouvez supprimer que vos propres recettes.', 'warning')
        return redirect(url_for('web_pages.recettes'))
    nom = r.nom
    db.session.delete(r)
    db.session.commit()
    flash(f'Recette « {nom} » supprimée.', 'success')
    return redirect(url_for('web_pages.recettes'))


# ==================================================
# DÉPENSES
# ==================================================
@web_pages_bp.route('/depenses', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def depenses():
    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        categorie = (request.form.get('categorie') or 'Autre').strip()
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
            d = Depense(
                user_id=current_user.id,
                nom=nom, categorie=categorie,
                date=date_str, heure=heure,
                montant=montant_val, devise=devise,
                description=description,
            )
            db.session.add(d)
            db.session.commit()
            flash(f'Dépense « {nom} » enregistrée ✅', 'success')
            return redirect(url_for('web_pages.depenses'))

    # ✅ PARTAGÉ : toutes les dépenses de tout le monde
    mes_depenses = (Depense.query
                    .order_by(Depense.date.desc(), Depense.id.desc())
                    .all())
    total = sum(d.montant for d in mes_depenses)
    total_recettes = _total_recettes()
    solde_net = total_recettes - total

    return render_template(
        'depenses.html',
        depenses=mes_depenses,
        total=total,
        total_recettes=total_recettes,
        solde_net=solde_net,
        categories=CATEGORIES_DEPENSES,
    )


@web_pages_bp.route('/depenses/<int:depense_id>/edit', methods=['POST'])
@login_required
def depense_edit(depense_id):
    d = db.session.get(Depense, depense_id)
    if not d:
        flash('Dépense introuvable.', 'error')
        return redirect(url_for('web_pages.depenses'))
    if d.user_id != current_user.id and not _is_admin():
        flash('Vous ne pouvez modifier que vos propres dépenses.', 'warning')
        return redirect(url_for('web_pages.depenses'))

    nom = (request.form.get('nom') or '').strip()
    categorie = (request.form.get('categorie') or 'Autre').strip()
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

    try:
        montant_val = float(montant_str)
        if montant_val <= 0:
            erreurs.append('Le montant doit être positif')
    except (ValueError, TypeError):
        erreurs.append('Montant invalide')
        montant_val = None

    if erreurs:
        for e in erreurs:
            flash(e, 'error')
    else:
        d.nom = nom
        d.categorie = categorie
        d.date = date_str
        d.heure = heure
        d.montant = montant_val
        d.devise = devise
        d.description = description
        db.session.commit()
        flash(f'Dépense « {nom} » modifiée ✅', 'success')

    return redirect(url_for('web_pages.depenses'))


@web_pages_bp.route('/depenses/<int:depense_id>/delete', methods=['POST'])
@login_required
def depense_delete(depense_id):
    d = db.session.get(Depense, depense_id)
    if not d:
        flash('Dépense introuvable.', 'error')
        return redirect(url_for('web_pages.depenses'))
    if d.user_id != current_user.id and not _is_admin():
        flash('Vous ne pouvez supprimer que vos propres dépenses.', 'warning')
        return redirect(url_for('web_pages.depenses'))
    nom = d.nom
    db.session.delete(d)
    db.session.commit()
    flash(f'Dépense « {nom} » supprimée.', 'success')
    return redirect(url_for('web_pages.depenses'))


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

    # ✅ PARTAGÉ : toutes les marchandises de tout le monde
    mes_marchandises = (Marchandise.query
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


@web_pages_bp.route('/marchandises/<int:m_id>/edit', methods=['POST'])
@login_required
def marchandise_edit(m_id):
    m = db.session.get(Marchandise, m_id)
    if not m:
        flash('Marchandise introuvable.', 'error')
        return redirect(url_for('web_pages.marchandises'))
    if m.user_id != current_user.id and not _is_admin():
        flash('Vous ne pouvez modifier que vos propres marchandises.', 'warning')
        return redirect(url_for('web_pages.marchandises'))

    nom = (request.form.get('nom') or '').strip()
    description = (request.form.get('description') or '').strip()
    prix_str = (request.form.get('prix_unitaire') or '').strip()
    qte_str = (request.form.get('quantite') or '').strip()
    red_str = (request.form.get('reduction_pct') or '0').strip()
    devise = (request.form.get('devise') or 'CDF').strip()

    erreurs = []
    if not nom:
        erreurs.append('Le nom est obligatoire')

    try:
        prix_val = float(prix_str)
        if prix_val <= 0:
            erreurs.append('Le prix doit être positif')
    except (ValueError, TypeError):
        erreurs.append('Prix unitaire invalide')
        prix_val = None

    try:
        qte_val = float(qte_str)
        if qte_val <= 0:
            erreurs.append('La quantité doit être positive')
    except (ValueError, TypeError):
        erreurs.append('Quantité invalide')
        qte_val = None

    try:
        red_val = float(red_str) if red_str else 0.0
        if red_val < 0 or red_val > 100:
            erreurs.append('La réduction doit être entre 0 et 100')
    except (ValueError, TypeError):
        erreurs.append('Réduction invalide')
        red_val = 0.0

    if erreurs:
        for e in erreurs:
            flash(e, 'error')
    else:
        m.nom = nom
        m.description = description
        m.prix_unitaire = prix_val
        m.quantite = qte_val
        m.reduction_pct = red_val
        m.devise = devise
        db.session.commit()
        flash(f'Marchandise « {nom} » modifiée ✅', 'success')

    return redirect(url_for('web_pages.marchandises'))


@web_pages_bp.route('/marchandises/<int:m_id>/delete', methods=['POST'])
@login_required
def marchandise_delete(m_id):
    m = db.session.get(Marchandise, m_id)
    if not m:
        flash('Marchandise introuvable.', 'error')
        return redirect(url_for('web_pages.marchandises'))
    if m.user_id != current_user.id and not _is_admin():
        flash('Vous ne pouvez supprimer que vos propres marchandises.', 'warning')
        return redirect(url_for('web_pages.marchandises'))
    nom = m.nom
    db.session.delete(m)
    db.session.commit()
    flash(f'Marchandise « {nom} » supprimée.', 'success')
    return redirect(url_for('web_pages.marchandises'))


# ==================================================
# STATS
# ==================================================
@web_pages_bp.route('/stats', strict_slashes=False)
@login_required
def stats():
    # ✅ PARTAGÉ : toutes les recettes
    mes_recettes = Recette.query.all()
    nb_recettes = len(mes_recettes)
    total_recettes = sum(r.montant for r in mes_recettes)

    recettes_par_devise = {}
    for r in mes_recettes:
        recettes_par_devise[r.devise] = recettes_par_devise.get(r.devise, 0) + r.montant

    # ✅ PARTAGÉ : toutes les dépenses
    mes_depenses = Depense.query.all()
    nb_depenses = len(mes_depenses)
    total_depenses = sum(d.montant for d in mes_depenses)

    depenses_par_devise = {}
    for d in mes_depenses:
        depenses_par_devise[d.devise] = depenses_par_devise.get(d.devise, 0) + d.montant

    depenses_par_categorie = {}
    for d in mes_depenses:
        depenses_par_categorie[d.categorie] = (
            depenses_par_categorie.get(d.categorie, 0) + d.montant
        )

    # ✅ PARTAGÉ : toutes les marchandises
    mes_marchandises = Marchandise.query.all()
    nb_marchandises = len(mes_marchandises)
    total_brut = sum(m.prix_total_brut for m in mes_marchandises)
    total_net = sum(m.prix_total_net for m in mes_marchandises)
    total_reductions = total_brut - total_net

    marchandises_par_devise = {}
    for m in mes_marchandises:
        marchandises_par_devise[m.devise] = (
            marchandises_par_devise.get(m.devise, 0) + m.prix_total_net
        )

    devises = set(recettes_par_devise) | set(depenses_par_devise)
    solde_par_devise = {}
    for dv in devises:
        solde_par_devise[dv] = (
            recettes_par_devise.get(dv, 0) - depenses_par_devise.get(dv, 0)
        )

    return render_template(
        'stats.html',
        nb_recettes=nb_recettes,
        total_recettes=total_recettes,
        recettes_par_devise=recettes_par_devise,
        nb_depenses=nb_depenses,
        total_depenses=total_depenses,
        depenses_par_devise=depenses_par_devise,
        depenses_par_categorie=depenses_par_categorie,
        nb_marchandises=nb_marchandises,
        total_brut=total_brut,
        total_net=total_net,
        total_reductions=total_reductions,
        marchandises_par_devise=marchandises_par_devise,
        solde_par_devise=solde_par_devise,
    )


# ==================================================
# EXPORT CSV
# ==================================================
def _csv_response(rows, headers, filename):
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@web_pages_bp.route('/recettes/export', strict_slashes=False)
@login_required
def recettes_export():
    # ✅ PARTAGÉ : on exporte toutes les recettes
    mes_recettes = (Recette.query
                    .order_by(Recette.date.desc(), Recette.id.desc())
                    .all())
    headers = ['ID', 'Nom', 'Jour', 'Date', 'Heure', 'Montant', 'Devise', 'Description']
    rows = [[r.id, r.nom, r.jour, r.date, r.heure,
             f'{r.montant:.2f}', r.devise, r.description or ''] for r in mes_recettes]
    return _csv_response(rows, headers, f'recettes_{datetime.now().strftime("%Y%m%d")}.csv')


@web_pages_bp.route('/depenses/export', strict_slashes=False)
@login_required
def depenses_export():
    mes_depenses = (Depense.query
                    .order_by(Depense.date.desc(), Depense.id.desc())
                    .all())
    headers = ['ID', 'Nom', 'Catégorie', 'Date', 'Heure', 'Montant', 'Devise', 'Description']
    rows = [[d.id, d.nom, d.categorie, d.date, d.heure,
             f'{d.montant:.2f}', d.devise, d.description or ''] for d in mes_depenses]
    return _csv_response(rows, headers, f'depenses_{datetime.now().strftime("%Y%m%d")}.csv')


@web_pages_bp.route('/marchandises/export', strict_slashes=False)
@login_required
def marchandises_export():
    mes_marchandises = (Marchandise.query
                        .order_by(Marchandise.created_at.desc())
                        .all())
    headers = ['ID', 'Nom', 'Description', 'Prix unitaire', 'Quantité',
               'Réduction %', 'Brut', 'Net', 'Devise']
    rows = [[m.id, m.nom, m.description or '', f'{m.prix_unitaire:.2f}',
             m.quantite, m.reduction_pct, f'{m.prix_total_brut:.2f}',
             f'{m.prix_total_net:.2f}', m.devise] for m in mes_marchandises]
    return _csv_response(rows, headers, f'marchandises_{datetime.now().strftime("%Y%m%d")}.csv')


# ==================================================
# CONTEXT PROCESSOR — Solde global (home)
# ==================================================
@web_pages_bp.context_processor
def injecter_solde_global():
    from flask import request
    if not current_user.is_authenticated:
        return {}
    if request.path not in ('/', '/home'):
        return {}
    total_recettes = _total_recettes()
    total_depenses = _total_depenses()
    return {
        'solde_global': total_recettes - total_depenses,
        'total_recettes_global': total_recettes,
        'total_depenses_global': total_depenses,
    }


# ==================================================
# CONTEXT PROCESSOR — Admin
# ==================================================
@web_pages_bp.context_processor
def injecter_donnees_admin():
    from flask import request
    if not _is_admin():
        return {}
    if not request.path.startswith('/admin'):
        return {}

    from models import User

    users = User.query.order_by(User.created_at.desc()).all()
    recettes = Recette.query.order_by(Recette.created_at.desc()).all()
    marchandises = Marchandise.query.order_by(Marchandise.created_at.desc()).all()
    depenses = Depense.query.order_by(Depense.created_at.desc()).all()

    total_recettes = sum(r.montant for r in recettes)
    total_brut = sum(m.prix_total_brut for m in marchandises)
    total_net = sum(m.prix_total_net for m in marchandises)
    total_red = total_brut - total_net
    total_depenses = sum(d.montant for d in depenses)

    return {
        'admin_users': users,
        'admin_recettes': recettes,
        'admin_marchandises': marchandises,
        'admin_depenses': depenses,
        'admin_total_recettes': total_recettes,
        'admin_total_brut': total_brut,
        'admin_total_net': total_net,
        'admin_total_red': total_red,
        'admin_total_depenses': total_depenses,
    }


# ==================================================
# ADMIN — Actions
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
    if new_role == 'admin':
        flash("Un seul admin est autorisé (défini dans la configuration).", 'warning')
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
    Recette.query.filter_by(user_id=user_id).delete()
    Marchandise.query.filter_by(user_id=user_id).delete()
    Depense.query.filter_by(user_id=user_id).delete()
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


@web_pages_bp.route('/admin/depenses/<int:d_id>/delete', methods=['POST'])
@login_required
def admin_delete_depense(d_id):
    if not _is_admin():
        flash("Accès réservé à l'administrateur.", 'error')
        return redirect(url_for('pages.home'))
    d = db.session.get(Depense, d_id)
    if not d:
        flash('Dépense introuvable.', 'error')
        return redirect(url_for('pages.admin'))
    nom = d.nom
    db.session.delete(d)
    db.session.commit()
    flash(f'Dépense « {nom} » supprimée.', 'success')
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
    
@web_pages_bp.before_app_request
def update_online_status():
    from flask_login import current_user
    from datetime import datetime as _dt
    from extensions import db

    if current_user.is_authenticated:
        now = _dt.utcnow()
        # Session terminée si last_seen > 2 min OU online_since jamais initialisé
        if (not current_user.online_since
                or not current_user.last_seen
                or (now - current_user.last_seen).total_seconds() > 120):
            current_user.online_since = now
        current_user.last_seen = now
        db.session.commit()
        
@web_pages_bp.app_context_processor
def injecter_solde_header():
    if not current_user.is_authenticated:
        return {}
    recettes = (db.session.query(db.func.coalesce(db.func.sum(Recette.montant), 0))
                .scalar() or 0)
    depenses = (db.session.query(db.func.coalesce(db.func.sum(Depense.montant), 0))
                .scalar() or 0)
    return {'solde_header': recettes - depenses}
