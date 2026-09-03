from flask import Blueprint, jsonify, request

from app.auth import require_api_key
from app.extensions import db
from app.models import Technician

bp = Blueprint("resources", __name__, url_prefix="/api/resource")


@bp.get("")
def list_resources():
    actif = request.args.get("actif")
    query = Technician.query
    if actif is not None:
        query = query.filter_by(actif=actif.lower() in ("1", "true", "oui"))
    technicians = query.order_by(Technician.nom).all()
    return jsonify([t.to_dict() for t in technicians])


@bp.get("/<int:resource_id>")
def get_resource(resource_id):
    technician = Technician.query.get_or_404(resource_id)
    return jsonify(technician.to_dict())


@bp.post("")
@require_api_key
def create_resource():
    data = request.get_json(silent=True) or {}
    if not data.get("nom") or not data.get("prenom"):
        return jsonify({"error": "nom et prenom sont requis"}), 400

    technician = Technician(
        nom=data["nom"],
        prenom=data["prenom"],
        email=data.get("email"),
        equipe=data.get("equipe"),
        couleur=data.get("couleur", "#007AFF"),
        actif=data.get("actif", True),
    )
    db.session.add(technician)
    db.session.commit()
    return jsonify(technician.to_dict()), 201


@bp.put("/<int:resource_id>")
@require_api_key
def update_resource(resource_id):
    technician = Technician.query.get_or_404(resource_id)
    data = request.get_json(silent=True) or {}

    for field in ("nom", "prenom", "email", "equipe", "couleur", "actif"):
        if field in data:
            setattr(technician, field, data[field])

    db.session.commit()
    return jsonify(technician.to_dict())


@bp.delete("/<int:resource_id>")
@require_api_key
def delete_resource(resource_id):
    technician = Technician.query.get_or_404(resource_id)
    db.session.delete(technician)
    db.session.commit()
    return "", 204
