from datetime import datetime

from flask import Blueprint, jsonify, request

from app.auth import require_api_key
from app.extensions import db
from app.models import Event, Technician

bp = Blueprint("events", __name__, url_prefix="/api/do/events")


def _parse_datetime(value, field_name):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} doit être une date ISO 8601 valide")


@bp.get("")
def list_events():
    query = Event.query

    resource_id = request.args.get("resourceId")
    if resource_id is not None:
        query = query.filter_by(resource_id=resource_id)

    is_unavailability = request.args.get("isUnavailability")
    if is_unavailability is not None:
        query = query.filter_by(
            is_unavailability=is_unavailability.lower() in ("1", "true", "oui")
        )

    start_after = request.args.get("start")
    if start_after:
        try:
            query = query.filter(Event.start >= _parse_datetime(start_after, "start"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    end_before = request.args.get("end")
    if end_before:
        try:
            query = query.filter(Event.end <= _parse_datetime(end_before, "end"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    events = query.order_by(Event.start).all()
    return jsonify([e.to_dict() for e in events])


@bp.get("/<int:event_id>")
def get_event(event_id):
    event = Event.query.get_or_404(event_id)
    return jsonify(event.to_dict())


@bp.post("")
@require_api_key
def create_event():
    data = request.get_json(silent=True) or {}

    for field in ("resourceId", "titre", "start", "end"):
        if not data.get(field):
            return jsonify({"error": f"{field} est requis"}), 400

    if not db.session.get(Technician, data["resourceId"]):
        return jsonify({"error": "resourceId inconnu"}), 400

    try:
        start = _parse_datetime(data["start"], "start")
        end = _parse_datetime(data["end"], "end")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if end <= start:
        return jsonify({"error": "end doit être postérieur à start"}), 400

    event = Event(
        resource_id=data["resourceId"],
        titre=data["titre"],
        description=data.get("description"),
        start=start,
        end=end,
        is_unavailability=data.get("isUnavailability", False),
        couleur=data.get("couleur"),
    )
    db.session.add(event)
    db.session.commit()
    return jsonify(event.to_dict()), 201


@bp.put("/<int:event_id>")
@require_api_key
def update_event(event_id):
    event = Event.query.get_or_404(event_id)
    data = request.get_json(silent=True) or {}

    if "resourceId" in data:
        if not db.session.get(Technician, data["resourceId"]):
            return jsonify({"error": "resourceId inconnu"}), 400
        event.resource_id = data["resourceId"]

    if "start" in data:
        try:
            event.start = _parse_datetime(data["start"], "start")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    if "end" in data:
        try:
            event.end = _parse_datetime(data["end"], "end")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    if event.end <= event.start:
        return jsonify({"error": "end doit être postérieur à start"}), 400

    for field, attr in (
        ("titre", "titre"),
        ("description", "description"),
        ("isUnavailability", "is_unavailability"),
        ("couleur", "couleur"),
    ):
        if field in data:
            setattr(event, attr, data[field])

    db.session.commit()
    return jsonify(event.to_dict())


@bp.delete("/<int:event_id>")
@require_api_key
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return "", 204
