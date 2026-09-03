from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import Event, Technician, User

app = create_app()

with app.app_context():
    db.create_all()

    if not User.query.filter_by(role="admin").first():
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Compte admin créé : admin / admin123")

    if not Technician.query.first():
        alice = Technician(nom="Dupont", prenom="Alice", email="alice@vitalya.fr", equipe="Nord")
        bob = Technician(nom="Martin", prenom="Bob", email="bob@vitalya.fr", equipe="Sud")
        db.session.add_all([alice, bob])
        db.session.commit()

        alice_user = User(username="alice", role="technicien", technician_id=alice.id)
        alice_user.set_password("alice123")
        db.session.add(alice_user)
        db.session.commit()
        print("Compte technicien créé : alice / alice123")

        start = datetime.utcnow().replace(hour=8, minute=0, second=0, microsecond=0)
        db.session.add_all(
            [
                Event(
                    resource_id=alice.id,
                    titre="Intervention client X",
                    start=start,
                    end=start + timedelta(hours=3),
                ),
                Event(
                    resource_id=bob.id,
                    titre="Congé",
                    start=start,
                    end=start + timedelta(days=1),
                    is_unavailability=True,
                ),
            ]
        )
        db.session.commit()
        print("Données de démonstration créées.")
    else:
        print("Des données existent déjà, rien à faire.")
