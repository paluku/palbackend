"""
Messagerie interne + statut en ligne + suppression automatique après lecture.
"""
from datetime import datetime, timedelta

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from flask_login import login_required, current_user

from extensions import db
from models import User, Message

web_messages_bp = Blueprint('web_messages', __name__)

# Délai (secondes) avant suppression d'un message lu
DELAI_SUPPRESSION = 20


# ==================================================
# PING — mise à jour du last_seen
# ==================================================
@web_messages_bp.route('/api/ping', methods=['POST'], strict_slashes=False)
@login_required
def ping():
    current_user.last_seen = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})


# ==================================================
# LISTE DES CONVERSATIONS
# ==================================================
@web_messages_bp.route('/messages', strict_slashes=False)
@login_required
def messages():
    autres = User.query.filter(User.id != current_user.id).order_by(User.nom).all()

    conversations = []
    for u in autres:
        non_lus = (Message.query
                   .filter_by(sender_id=u.id, recipient_id=current_user.id, lu=False)
                   .count())
        dernier = (Message.query
                   .filter(
                       db.or_(
                           db.and_(Message.sender_id == current_user.id,
                                   Message.recipient_id == u.id),
                           db.and_(Message.sender_id == u.id,
                                   Message.recipient_id == current_user.id)
                       )
                   )
                   .order_by(Message.created_at.desc())
                   .first())
        conversations.append({
            'user': u,
            'non_lus': non_lus,
            'dernier': dernier,
        })

    conversations.sort(
        key=lambda c: (c['non_lus'] > 0,
                       c['dernier'].created_at if c['dernier'] else datetime.min),
        reverse=True
    )

    return render_template('messages.html', conversations=conversations)


# ==================================================
# CONVERSATION AVEC UN UTILISATEUR
# ==================================================
@web_messages_bp.route('/messages/<int:user_id>', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def conversation(user_id):
    autre = db.session.get(User, user_id)
    if not autre or autre.id == current_user.id:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('web_messages.messages'))

    if request.method == 'POST':
        contenu = (request.form.get('contenu') or '').strip()
        if not contenu:
            flash('Le message ne peut pas être vide.', 'error')
        else:
            msg = Message(
                sender_id=current_user.id,
                recipient_id=autre.id,
                contenu=contenu,
                lu=False,
            )
            db.session.add(msg)
            db.session.commit()
            return redirect(url_for('web_messages.conversation', user_id=autre.id))

    # Marquer comme lus les messages reçus
    Message.query.filter_by(
        sender_id=autre.id, recipient_id=current_user.id
    ).update({'lu': True, 'read_at': datetime.utcnow()})
    db.session.commit()

    # Charger la conversation (après la mise à jour read_at)
    messages_liste = (Message.query
                      .filter(
                          db.or_(
                              db.and_(Message.sender_id == current_user.id,
                                      Message.recipient_id == autre.id),
                              db.and_(Message.sender_id == autre.id,
                                      Message.recipient_id == current_user.id)
                          )
                      )
                      .order_by(Message.created_at.asc())
                      .all())

    current_user.last_seen = datetime.utcnow()
    db.session.commit()

    return render_template(
        'conversation.html',
        autre=autre,
        messages_liste=messages_liste,
        delai_suppression=DELAI_SUPPRESSION,
    )


# ==================================================
# API — compteur de non-lus (badge menu)
# ==================================================
@web_messages_bp.route('/api/messages/unread', strict_slashes=False)
@login_required
def unread_count():
    count = (Message.query
             .filter_by(recipient_id=current_user.id, lu=False)
             .count())
    return jsonify({'unread': count})


# ==================================================
# API — messages d'une conversation (polling)
# ==================================================
@web_messages_bp.route('/api/messages/<int:user_id>', strict_slashes=False)
@login_required
def api_conversation(user_id):
    autre = db.session.get(User, user_id)
    if not autre:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    messages_liste = (Message.query
                      .filter(
                          db.or_(
                              db.and_(Message.sender_id == current_user.id,
                                      Message.recipient_id == autre.id),
                              db.and_(Message.sender_id == autre.id,
                                      Message.recipient_id == current_user.id)
                          )
                      )
                      .order_by(Message.created_at.asc())
                      .all())

    return jsonify({
        'messages': [m.to_dict() for m in messages_liste],
        'current_user_id': current_user.id,
    })


# ==================================================
# API — purge des messages lus (burn-after-read)
# ==================================================
@web_messages_bp.route('/api/messages/purge', methods=['POST'], strict_slashes=False)
@login_required
def purge_read_messages():
    """Supprime les messages reçus et lus il y a plus de (DELAI_SUPPRESSION - 5) sec."""
    seuil = datetime.utcnow() - timedelta(seconds=DELAI_SUPPRESSION - 5)
    deleted = Message.query.filter(
        Message.recipient_id == current_user.id,
        Message.read_at.isnot(None),
        Message.read_at <= seuil
    ).delete()
    db.session.commit()
    return jsonify({'deleted': deleted, 'ok': True})