"""
API JSON messagerie — Flutter + React.
"""
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from extensions import db
from models import User, Message

api_messages_bp = Blueprint('api_messages', __name__, url_prefix='/api/messages')

DELAI_SUPPRESSION = 20  # secondes


# ==================================================
# LISTE DES UTILISATEURS (pour démarrer une conversation)
# ==================================================
@api_messages_bp.route('/users', methods=['GET'], strict_slashes=False)
@jwt_required()
def list_users():
    users = User.query.filter(User.id != current_user.id).order_by(User.nom).all()
    return jsonify({
        'success': True,
        'users': [
            {
                'id': u.id,
                'nom': u.nom,
                'is_admin': u.is_admin,
                'is_online': u.is_online,
            }
            for u in users
        ],
    })


# ==================================================
# LISTE DES CONVERSATIONS
# ==================================================
@api_messages_bp.route('', methods=['GET'], strict_slashes=False)
@jwt_required()
def list_conversations():
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
            'user': {
                'id': u.id,
                'nom': u.nom,
                'is_admin': u.is_admin,
                'is_online': u.is_online,
            },
            'non_lus': non_lus,
            'dernier': {
                'contenu': dernier.contenu if dernier else None,
                'sender_id': dernier.sender_id if dernier else None,
                'created_at': dernier.created_at.strftime('%d/%m %H:%M') if dernier else None,
            } if dernier else None,
        })

    conversations.sort(
        key=lambda c: (
            c['non_lus'] > 0,
            c['dernier']['created_at'] if c['dernier'] else ''
        ),
        reverse=True,
    )

    return jsonify({'success': True, 'conversations': conversations})


# ==================================================
# COMPTEUR NON-LUS (badge)
# ==================================================
@api_messages_bp.route('/unread', methods=['GET'], strict_slashes=False)
@jwt_required()
def unread_count():
    count = (Message.query
             .filter_by(recipient_id=current_user.id, lu=False)
             .count())
    return jsonify({'unread': count})


# ==================================================
# CONVERSATION AVEC UN UTILISATEUR
# ==================================================
@api_messages_bp.route('/<int:user_id>', methods=['GET'], strict_slashes=False)
@jwt_required()
def get_conversation(user_id):
    autre = db.session.get(User, user_id)
    if not autre:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    # Marquer les messages reçus comme lus
    Message.query.filter_by(
        sender_id=autre.id, recipient_id=current_user.id
    ).update({'lu': True, 'read_at': datetime.utcnow()})
    db.session.commit()

    messages = (Message.query
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

    return jsonify({
        'success': True,
        'autre': {
            'id': autre.id,
            'nom': autre.nom,
            'is_admin': autre.is_admin,
            'is_online': autre.is_online,
        },
        'current_user_id': current_user.id,
        'messages': [m.to_dict() for m in messages],
        'delai_suppression': DELAI_SUPPRESSION,
    })


# ==================================================
# ENVOYER UN MESSAGE
# ==================================================
@api_messages_bp.route('/<int:user_id>', methods=['POST'], strict_slashes=False)
@jwt_required()
def send_message(user_id):
    autre = db.session.get(User, user_id)
    if not autre or autre.id == current_user.id:
        return jsonify({'error': 'Destinataire invalide'}), 400

    data = request.get_json(silent=True) or {}
    contenu = (data.get('contenu') or '').strip()

    if not contenu:
        return jsonify({'error': 'Le message ne peut pas être vide'}), 400

    m = Message(
        sender_id=current_user.id,
        recipient_id=autre.id,
        contenu=contenu,
        lu=False,
    )
    db.session.add(m)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': m.to_dict(),
    }), 201


# ==================================================
# PURGE (suppression des messages lus)
# ==================================================
@api_messages_bp.route('/purge', methods=['POST'], strict_slashes=False)
@jwt_required()
def purge_read():
    seuil = datetime.utcnow() - timedelta(seconds=DELAI_SUPPRESSION - 5)
    deleted = Message.query.filter(
        Message.recipient_id == current_user.id,
        Message.read_at.isnot(None),
        Message.read_at <= seuil,
    ).delete()
    db.session.commit()
    return jsonify({'deleted': deleted, 'ok': True})