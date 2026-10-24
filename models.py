"""
Modèles SQLAlchemy : User, TokenBlocklist, ActivityLog,
Recette, Marchandise, Depense, Message.
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


# ==================== UTILISATEUR ====================
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), default='user')
    email_verified = db.Column(db.Boolean, default=False)
    failed_logins = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    online_since = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        from flask import current_app
        try:
            admin_email = current_app.config.get('ADMIN_EMAIL', '')
            return bool(admin_email) and self.email == admin_email
        except Exception:
            return self.role == 'admin'

    @property
    def is_online(self):
        if not self.last_seen:
            return False
        return (datetime.utcnow() - self.last_seen).total_seconds() < 120

    @property
    def online_since_display(self):
        ts = self.online_since or self.last_seen
        if not ts:
            return "à l'instant"
        delta = datetime.utcnow() - ts
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            return "à l'instant"
        if minutes < 60:
            return f"depuis {minutes} min"
        return f"depuis {ts.strftime('%H:%M')}"
    
    
    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'email': self.email,
            'role': self.role,
            'is_admin': self.is_admin,           # ← AJOUT
            'email_verified': self.email_verified,
            'created_at': self.created_at.strftime('%d/%m/%Y') if self.created_at else '',
            'is_online': self.is_online,
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'

    # ---------- mot de passe ----------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ---------- admin ----------
    @property
    def is_admin(self):
        from flask import current_app
        try:
            admin_email = current_app.config.get('ADMIN_EMAIL', '')
            return bool(admin_email) and self.email == admin_email
        except Exception:
            return self.role == 'admin'

    # ---------- statut en ligne ----------
    @property
    def is_online(self):
        if not self.last_seen:
            return False
        return (datetime.utcnow() - self.last_seen).total_seconds() < 120

    # ---------- sérialisation ----------
    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'email': self.email,
            'role': self.role,
            'email_verified': self.email_verified,
            'created_at': self.created_at.strftime('%d/%m/%Y') if self.created_at else '',
            'is_online': self.is_online,
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


# ==================== TOKENS RÉVOQUÉS (JWT) ====================
class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True, unique=True)
    type = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==================== LOGS D'ACTIVITÉ ====================
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(255))
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='logs')


# ==================== RECETTES ====================
class Recette(db.Model):
    __tablename__ = 'recettes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    nom = db.Column(db.String(150), nullable=False)
    jour = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(10), nullable=False, index=True)
    heure = db.Column(db.String(5), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    devise = db.Column(db.String(3), nullable=False, default='CDF')
    description = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    auteur = db.relationship('User', foreign_keys=[user_id])

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
    reduction_pct = db.Column(db.Float, default=0)
    devise = db.Column(db.String(3), nullable=False, default='CDF')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    auteur = db.relationship('User', foreign_keys=[user_id])

    @property
    def prix_total_brut(self):
        return self.prix_unitaire * self.quantite

    @property
    def montant_reduction(self):
        return self.prix_total_brut * (self.reduction_pct / 100)

    @property
    def prix_total_net(self):
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


# ==================== DÉPENSES ====================
class Depense(db.Model):
    __tablename__ = 'depenses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    nom = db.Column(db.String(150), nullable=False)
    categorie = db.Column(db.String(50), default='Autre', nullable=False)
    date = db.Column(db.String(10), nullable=False, index=True)
    heure = db.Column(db.String(5), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    devise = db.Column(db.String(3), nullable=False, default='CDF')
    description = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    auteur = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'categorie': self.categorie,
            'date': self.date,
            'heure': self.heure,
            'montant': self.montant,
            'devise': self.devise,
            'description': self.description,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else '',
        }


# ==================== MESSAGES (burn-after-read) ====================
class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    contenu = db.Column(db.Text, nullable=False)
    lu = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    sender = db.relationship('User', foreign_keys=[sender_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'contenu': self.contenu,
            'lu': self.lu,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else '',
        }
