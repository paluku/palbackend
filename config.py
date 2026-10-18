import os
from datetime import timedelta
from dotenv import load_dotenv

# Charge le fichier .env (à la racine du projet)
load_dotenv()


class Config:
    # ==================== SÉCURITÉ ====================
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-changez-moi')

    # ==================== BASE DE DONNÉES ====================
    # Lit DATABASE_URL (PostgreSQL Aiven) avec fallback SQLite en local
    _db_url = os.getenv('DATABASE_URL', 'sqlite:///saas_auth.db')

    # SQLAlchemy 2.x exige le préfixe 'postgresql://' (pas 'postgres://')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ==================== URL DE BASE ====================
    BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1:5000')

    # ==================== ADMIN UNIQUE ====================
    # Seul cet email est considéré comme admin (propriété is_admin)
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'paluku.kasai@gmail.com')

    # ==================== MAIL ====================
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'SaaS <noreply@saas.fr>')

    # ==================== LIMITER ====================
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')

    # ==================== JWT (pour Flutter) ====================
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_ERROR_MESSAGE_KEY = 'error'

    # ==================== CORS ====================
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')