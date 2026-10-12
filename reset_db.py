"""
Script de réinitialisation de la base de données.
Supprime TOUTES les tables puis les recrée + recrée l'admin par défaut.

Usage :
    python reset_db.py
"""
from app import app
from extensions import db
from models import User


def reset_database():
    with app.app_context():
        print("=" * 55)
        print("🗑️  RÉINITIALISATION DE LA BASE")
        print("=" * 55)

        # 1. Supprime toutes les tables
        print("→ Suppression des tables...")
        db.drop_all()
        print("   ✅ Tables supprimées")

        # 2. Recrée les tables
        print("→ Création des tables...")
        db.create_all()
        print("   ✅ Tables créées")

        # 3. Recrée l'admin par défaut
        print("→ Création de l'admin par défaut...")
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
            print("   👑 Admin créé : paluku.kasai@gmail.com / admin123")
        else:
            print("   ℹ️  Admin déjà présent")

        print()
        print("✅ Base réinitialisée avec succès.")
        print("=" * 55)


if __name__ == '__main__':
    reset_database()