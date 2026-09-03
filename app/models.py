from datetime import datetime

from app.extensions import db


class Technician(db.Model):
    __tablename__ = "technicians"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    prenom = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    equipe = db.Column(db.String(120), nullable=True)
    couleur = db.Column(db.String(7), nullable=True, default="#007AFF")
    actif = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship(
        "Event", backref="resource", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "prenom": self.prenom,
            "email": self.email,
            "equipe": self.equipe,
            "couleur": self.couleur,
            "actif": self.actif,
        }


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(
        db.Integer, db.ForeignKey("technicians.id"), nullable=False
    )
    titre = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    is_unavailability = db.Column(db.Boolean, nullable=False, default=False)
    couleur = db.Column(db.String(7), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        duration = self.end - self.start
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes = remainder // 60
        return {
            "id": self.id,
            "resourceId": self.resource_id,
            "titre": self.titre,
            "description": self.description,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "isUnavailability": self.is_unavailability,
            "couleur": self.couleur,
            "duration": {"time": {"hour": hours, "minute": minutes}},
        }
