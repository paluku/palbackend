"""
Script de test — Vérifie la connexion à PostgreSQL (Aiven).
Usage : python test_aiven.py
"""
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    print("=" * 60)
    print("🔍 TEST DE CONNEXION — PostgreSQL Aiven")
    print("=" * 60)

    # 1. Vérifier que DATABASE_URL existe
    raw_url = os.environ.get('DATABASE_URL')
    if not raw_url:
        print("❌ DATABASE_URL n'est pas défini.")
        print()
        print("→ Crée un fichier .env à la racine avec :")
        print("   DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require")
        return

    # 2. Afficher l'URI (masquée)
    masked = raw_url
    if '@' in raw_url:
        before, after = raw_url.split('@', 1)
        masked = before.split(':')[0] + ':***@' + after
    print(f"📌 URI         : {masked[:70]}...")
    print(f"📌 Préfixe     : {raw_url.split('://')[0]}")

    # 3. Corriger le préfixe (comme dans config.py)
    db_url = raw_url
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
        print("🔄 Conversion  : postgres:// → postgresql://")

    if not db_url.startswith('postgresql://'):
        print(f"⚠️  Attention : l'URI ne commence pas par postgresql://")

    # 4. Vérifier la présence de sslmode=require
    if 'sslmode=require' in db_url:
        print("🔒 SSL         : require ✅")
    else:
        print("🔒 SSL         : ⚠️  sslmode=require manquant")

    # 5. Tester la connexion SQLAlchemy
    print()
    print("─" * 60)
    print("🔌 Test de connexion SQLAlchemy...")
    print("─" * 60)

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            if result == 1:
                print("✅ Connexion PostgreSQL : OK")

            # Version serveur
            version = conn.execute(text("SELECT version()")).scalar()
            print(f"📦 Serveur : {version.split(',')[0]}")

            # Base courante
            db_name = conn.execute(text("SELECT current_database()")).scalar()
            print(f"🗄️  Base    : {db_name}")

            # Utilisateur
            user = conn.execute(text("SELECT current_user")).scalar()
            print(f"👤 User    : {user}")

            # Tables existantes
            print()
            print("─" * 60)
            print("📋 Tables dans la base :")
            print("─" * 60)

            tables_query = text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = conn.execute(tables_query).fetchall()

            if tables:
                for t in tables:
                    # Compter les lignes dans chaque table
                    try:
                        count = conn.execute(
                            text(f'SELECT COUNT(*) FROM "{t[0]}"')
                        ).scalar()
                        print(f"   ✅ {t[0]:20s} ({count} ligne{'s' if count > 1 else ''})")
                    except Exception:
                        print(f"   ✅ {t[0]:20s}")
            else:
                print("   ⚠️  Aucune table trouvée")
                print("   → Lance `python app.py` pour créer les tables")

    except Exception as e:
        print(f"❌ ERREUR de connexion :")
        print(f"   {type(e).__name__}: {e}")
        print()
        print("💡 Solutions possibles :")
        print("   - Vérifie le mot de passe dans DATABASE_URL")
        print("   - Vérifie que ?sslmode=require est présent")
        print("   - Vérifie que l'IP autorise les connexions externes sur Aiven")
        return

    # 6. Tester la connexion via Flask
    print()
    print("─" * 60)
    print("🔌 Test via l'application Flask...")
    print("─" * 60)

    try:
        from app import app
        from extensions import db
        from models import User, Recette, Marchandise, Depense

        with app.app_context():
            flask_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if flask_uri.startswith('postgresql://'):
                print("✅ app.config utilise PostgreSQL")
            else:
                print(f"⚠️  app.config utilise : {flask_uri.split('://')[0]}")

            print(f"👥 Utilisateurs : {User.query.count()}")
            print(f"💰 Recettes     : {Recette.query.count()}")
            print(f"📦 Marchandises : {Marchandise.query.count()}")
            print(f"💸 Dépenses     : {Depense.query.count()}")

    except Exception as e:
        print(f"⚠️  Impossible de tester via Flask : {type(e).__name__}: {e}")

    print()
    print("=" * 60)
    print("✅ TEST TERMINÉ")
    print("=" * 60)


if __name__ == '__main__':
    main()