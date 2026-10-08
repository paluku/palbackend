"""
SaaS Auth — Backend d'authentification JWT indépendant.
Utilisable pour toute application Flutter / Web / mobile.
"""
import os
from datetime import datetime

from flask import (Flask, jsonify, request, redirect, url_for, g,
                   render_template)
from flask_login import current_user
from itsdangerous import URLSafeTimedSerializer

from config import Config
from extensions import db, login_manager, mail, limiter, jwt, cors
from models import User
from blueprints.api_recettes import api_recettes_bp
from blueprints.api_marchandises import api_marchandises_bp
from blueprints.api_stats import api_stats_bp


# ================================================================
# FACTORY
# ================================================================
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ==================== EXTENSIONS ====================
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    jwt.init_app(app)

    # ==================== CORS (pour Flutter) ====================
    cors.init_app(
          app,
        resources={r"/api/*": {
            "origins": "*",
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        }},
        supports_credentials=False,
    )

    # ==================== FLASK-LOGIN ====================
    login_manager.login_view = 'pages.login'
    login_manager.login_message = "Connectez-vous pour continuer."
    login_manager.login_message_category = 'warning'

    # ==================== SERIALIZER (reset password) ====================
    app.password_reset_serializer = URLSafeTimedSerializer(
        app.config['SECRET_KEY'], salt='saas-auth-tokens'
    )

    # ==================== BASE DE DONNÉES ====================
    with app.app_context():
        db.create_all()

        # Créer un admin par défaut s'il n'existe pas
        if not User.query.filter_by(email='paluku.kasai@gmail.com').first():
            admin = User(
                nom='Admin',
                email='paluku.kasai@gmail.com',
                role='admin',
                email_verified=True,
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("👑 Admin créé : paluku.kasai@gmail.com / admin123")

        print("✅ Base SQLite prête (saas_auth.db)")

    # ==================== UTILISATEUR COURANT ====================
    @app.before_request
    def charger_utilisateur():
        g.user = current_user if current_user.is_authenticated else None

    @app.context_processor
    def injecter_user():
        return dict(
            current_user=g.get('user'),
            annee=datetime.now().year,
        )

    # ==================== CALLBACKS JWT ====================
    from blueprints import jwt_callbacks  # noqa: F401

    # ==================== BLUEPRINTS ====================
    from blueprints.pages import pages_bp
    from blueprints.api_auth import api_auth_bp
    from blueprints.api_users import api_users_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_auth_bp)
    app.register_blueprint(api_users_bp)
    app.register_blueprint(api_recettes_bp)
    app.register_blueprint(api_marchandises_bp)
    app.register_blueprint(api_stats_bp)

    # ==================== GESTION D'ERREURS ====================
    @app.errorhandler(403)
    def e403(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Accès interdit'}), 403
        return "Accès interdit", 403

    @app.errorhandler(404)
    def e404(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Introuvable'}), 404
        return redirect(url_for('pages.home'))

    @app.errorhandler(405)
    def e405(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Méthode non autorisée'}), 405
        return redirect(url_for('pages.home'))

    @app.errorhandler(429)
    def e429(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Trop de requêtes'}), 429
        return "Trop de requêtes", 429

    @app.errorhandler(500)
    def e500(e):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Erreur interne'}), 500
        return "Erreur interne", 500

    return app


# ================================================================
# LANCEMENT
# ================================================================
app = create_app()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🔐 SaaS Auth — Backend indépendant")
    print("=" * 60)
    print("🌐 Web       : http://127.0.0.1:5000")
    print("🔐 Login     : http://127.0.0.1:5000/login")
    print("👤 Register  : http://127.0.0.1:5000/register")
    print("👑 Admin     : admin@saas.fr / admin123")
    print()
    print("📱 API JWT (Flutter) :")
    print("  POST  /api/auth/register")
    print("  POST  /api/auth/login")
    print("  POST  /api/auth/refresh")
    print("  POST  /api/auth/logout")
    print("  GET   /api/auth/me")
    print("  POST  /api/auth/change-password")
    print("  POST  /api/auth/forgot-password")
    print()
    print("  GET   /api/users          (admin)")
    print("  GET   /api/users/<id>")
    print("  PUT   /api/users/<id>/role (admin)")
    print("  DEL   /api/users/<id>      (admin)")
    print("=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5001)),
        debug=True,
    )