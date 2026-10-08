from flask import current_app, url_for
from flask_mail import Message
from extensions import mail


def envoyer_reset_password(user):
    """Envoie l'email de réinitialisation."""
    serializer = current_app.password_reset_serializer
    token = serializer.dumps({'user_id': user.id, 'type': 'reset'})

    lien = url_for('pages.reset_password', token=token, _external=True)

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:30px;">
      <h2 style="color:#2c3e50;">Bonjour {user.nom},</h2>
      <p>Vous avez demandé à réinitialiser votre mot de passe.</p>
      <p style="text-align:center;margin:30px 0;">
        <a href="{lien}" style="background:#f39c12;color:#fff;padding:14px 28px;
                                 border-radius:8px;text-decoration:none;font-weight:bold;">
          Réinitialiser mon mot de passe
        </a>
      </p>
      <p style="color:#94a3b8;font-size:.85rem;">Lien valable 1 heure.</p>
    </div>
    """
    msg = Message(
        subject="🔐 Réinitialisation de mot de passe",
        recipients=[user.email],
        html=html,
    )
    mail.send(msg)