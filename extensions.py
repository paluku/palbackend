from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
limiter = Limiter(key_func=get_remote_address)
jwt = JWTManager()
cors = CORS()


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))