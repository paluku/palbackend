from extensions import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # 'user' | 'moderator' | 'admin'
    role = db.Column(db.String(20), default='user')

    email_verified = db.Column(db.Boolean, default=False)
    failed_logins = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'email': self.email,
            'role': self.role,
            'email_verified': self.email_verified,
            'created_at': self.created_at.strftime('%d/%m/%Y') if self.created_at else '',
        }


class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True, unique=True)
    type = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(255))
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='logs')
    
    # ==================== RECETTES JOURNALIÈRES ====================
class Recette(db.Model):
    __tablename__ = 'recettes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    nom = db.Column(db.String(150), nullable=False)
    jour = db.Column(db.String(20), nullable=False)      # 'Lundi', 'Mardi'...
    date = db.Column(db.String(10), nullable=False, index=True)  # YYYY-MM-DD
    heure = db.Column(db.String(5), nullable=False)      # HH:MM
    montant = db.Column(db.Float, nullable=False)
    devise = db.Column(db.String(3), nullable=False, default='CDF')  # CDF, EUR, USD
    description = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'jour': self.jour,
            'date': self.date,
            'heure': self.heure,
            'montant': self.montant,
            'devise': self.devise,
            'description': self.description,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else '',
        }


# ==================== MARCHANDISES ====================
class Marchandise(db.Model):
    __tablename__ = 'marchandises'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    nom = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default='')
    prix_unitaire = db.Column(db.Float, nullable=False)
    quantite = db.Column(db.Float, nullable=False, default=1)
    reduction_pct = db.Column(db.Float, default=0)       # % de réduction
    devise = db.Column(db.String(3), nullable=False, default='CDF')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def prix_total_brut(self):
        """Prix × quantité, sans réduction."""
        return self.prix_unitaire * self.quantite

    @property
    def montant_reduction(self):
        """Montant de la réduction."""
        return self.prix_total_brut * (self.reduction_pct / 100)

    @property
    def prix_total_net(self):
        """Prix final après réduction."""
        return self.prix_total_brut - self.montant_reduction

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'description': self.description,
            'prix_unitaire': self.prix_unitaire,
            'quantite': self.quantite,
            'reduction_pct': self.reduction_pct,
            'devise': self.devise,
            'prix_total_brut': round(self.prix_total_brut, 2),
            'montant_reduction': round(self.montant_reduction, 2),
            'prix_total_net': round(self.prix_total_net, 2),
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else '',
        }