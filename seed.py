from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import Event, Technician

app = create_app()

with app.app_context():
    db.create_all()

    if not Technician.query.first():
        alice = Technician(nom="Dupont", prenom="Alice", email="alice@vitalya.fr", equipe="Nord")
        bob = Technician(nom="Martin", prenom="Bob", email="bob@vitalya.fr", equipe="Sud")
        db.session.add_all([alice, bob])
        db.session.commit()

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
