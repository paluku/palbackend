"""Test de la propriété online_since_display."""
from app import app
from models import User

with app.app_context():
    print("=" * 60)
    for u in User.query.all():
        print(f"ID = {u.id}")
        print(f"   nom                  = {u.nom}")
        print(f"   online_since         = {u.online_since}")
        print(f"   last_seen            = {u.last_seen}")
        print(f"   is_online            = {u.is_online}")
        print(f"   online_since_display = '{u.online_since_display}'")
        print("-" * 60)