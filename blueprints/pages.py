"""
Pages web (optionnel - pour tester dans le navigateur).
"""
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app)
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import BadSignature, SignatureExpired

from extensions import db
from models import User
from logs_utils import log_action

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/', strict_slashes=False)
def home():
    return render_template('home.html')


@pages_bp.route('/login', methods=['GET', 'POST'], strict_slashes=False)
def login():
    if current_user.is_authenticated:
        return redirect(url_for('pages.home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            log_action('web_login', email, user=user)
            return redirect(url_for('pages.home'))

        flash('Email ou mot de passe incorrect.', 'error')

    return render_template('login.html')


@pages_bp.route('/register', methods=['GET', 'POST'], strict_slashes=False)
def register():
    if current_user.is_authenticated:
        return redirect(url_for('pages.home'))

    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not nom or not email or len(password) < 6:
            flash('Champs invalides.', 'error')
            return render_template('register.html', nom=nom, email=email)

        if User.query.filter_by(email=email).first():
            flash('Email déjà utilisé.', 'error')
            return render_template('register.html', nom=nom, email=email)

        user = User(nom=nom, email=email, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        log_action('web_register', email, user=user)
        return redirect(url_for('pages.home'))

    return render_template('register.html')


@pages_bp.route('/logout', strict_slashes=False)
@login_required
def logout():
    logout_user()
    flash('Déconnecté.', 'success')
    return redirect(url_for('pages.login'))


@pages_bp.route('/users', strict_slashes=False)
@login_required
def users():
    tous = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=tous)


@pages_bp.route('/forgot-password', methods=['GET', 'POST'], strict_slashes=False)
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            from email_utils import envoyer_reset_password
            try:
                envoyer_reset_password(user)
            except Exception as e:
                print(f"⚠️ {e}")
        flash('Si un compte existe, un email a été envoyé.', 'success')
        return redirect(url_for('pages.login'))
    return render_template('forgot_password.html')


@pages_bp.route('/reset-password/<token>', methods=['GET', 'POST'], strict_slashes=False)
def reset_password(token):
    serializer = current_app.password_reset_serializer
    try:
        data = serializer.loads(token, max_age=3600)
    except (SignatureExpired, BadSignature):
        flash('Lien expiré ou invalide.', 'error')
        return redirect(url_for('pages.forgot_password'))

    user = User.query.get(data.get('user_id'))
    if not user:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('pages.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if len(password) < 6:
            flash('6 caractères minimum.', 'error')
        elif password != password2:
            flash('Les mots de passe diffèrent.', 'error')
        else:
            user.set_password(password)
            db.session.commit()
            flash('Mot de passe modifié.', 'success')
            return redirect(url_for('pages.login'))

    return render_template('reset_password.html', token=token, email=user.email)
    
@pages_bp.route('/admin', strict_slashes=False)
@login_required
def admin():
    """Page admin HTML pour tout gérer."""
    if not current_user.is_admin:
        flash('Accès réservé à l\'administrateur.', 'error')
        return redirect(url_for('pages.home'))
    return render_template('admin/dashboard.html')