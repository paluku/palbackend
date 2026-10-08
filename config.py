import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-changez-moi')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///saas_auth.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1:5000')

    # Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'SaaS <noreply@saas.fr>')

    # Limiter
    RATELIMIT_STORAGE_URI = 'memory://'

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_ERROR_MESSAGE_KEY = 'error'

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')