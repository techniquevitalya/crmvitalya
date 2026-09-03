import pytest

from app import create_app
from app.extensions import db


class TestConfig:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_KEY = "test-key"


@pytest.fixture
def client():
    app = create_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
        db.drop_all()


def auth_headers():
    return {"X-API-Key": "test-key"}


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_resource_requires_api_key(client):
    resp = client.post("/api/resource", json={"nom": "Dupont", "prenom": "Alice"})
    assert resp.status_code == 401


def test_create_resource_requires_fields(client):
    resp = client.post("/api/resource", json={"nom": "Dupont"}, headers=auth_headers())
    assert resp.status_code == 400


def test_create_and_list_resource(client):
    resp = client.post(
        "/api/resource",
        json={"nom": "Dupont", "prenom": "Alice", "equipe": "Nord"},
        headers=auth_headers(),
    )
    assert resp.status_code == 201
    technician_id = resp.get_json()["id"]

    resp = client.get("/api/resource")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1

    resp = client.get(f"/api/resource/{technician_id}")
    assert resp.status_code == 200
    assert resp.get_json()["nom"] == "Dupont"


def test_create_event_requires_known_resource(client):
    resp = client.post(
        "/api/do/events",
        json={
            "resourceId": 999,
            "titre": "Intervention",
            "start": "2026-01-01T08:00:00",
            "end": "2026-01-01T10:00:00",
        },
        headers=auth_headers(),
    )
    assert resp.status_code == 400


def test_create_event_rejects_end_before_start(client):
    resource = client.post(
        "/api/resource",
        json={"nom": "Dupont", "prenom": "Alice"},
        headers=auth_headers(),
    ).get_json()

    resp = client.post(
        "/api/do/events",
        json={
            "resourceId": resource["id"],
            "titre": "Intervention",
            "start": "2026-01-01T10:00:00",
            "end": "2026-01-01T08:00:00",
        },
        headers=auth_headers(),
    )
    assert resp.status_code == 400


def test_create_event_and_duration(client):
    resource = client.post(
        "/api/resource",
        json={"nom": "Dupont", "prenom": "Alice"},
        headers=auth_headers(),
    ).get_json()

    resp = client.post(
        "/api/do/events",
        json={
            "resourceId": resource["id"],
            "titre": "Intervention",
            "start": "2026-01-01T08:00:00",
            "end": "2026-01-01T10:30:00",
        },
        headers=auth_headers(),
    )
    assert resp.status_code == 201
    event = resp.get_json()
    assert event["duration"]["time"] == {"hour": 2, "minute": 30}
    assert event["isUnavailability"] is False


def test_filter_events_by_unavailability(client):
    resource = client.post(
        "/api/resource",
        json={"nom": "Dupont", "prenom": "Alice"},
        headers=auth_headers(),
    ).get_json()

    client.post(
        "/api/do/events",
        json={
            "resourceId": resource["id"],
            "titre": "Congé",
            "start": "2026-01-01T08:00:00",
            "end": "2026-01-02T08:00:00",
            "isUnavailability": True,
        },
        headers=auth_headers(),
    )
    client.post(
        "/api/do/events",
        json={
            "resourceId": resource["id"],
            "titre": "Intervention",
            "start": "2026-01-03T08:00:00",
            "end": "2026-01-03T10:00:00",
        },
        headers=auth_headers(),
    )

    resp = client.get("/api/do/events?isUnavailability=false")
    assert resp.status_code == 200
    events = resp.get_json()
    assert len(events) == 1
    assert events[0]["titre"] == "Intervention"


def test_delete_event(client):
    resource = client.post(
        "/api/resource",
        json={"nom": "Dupont", "prenom": "Alice"},
        headers=auth_headers(),
    ).get_json()

    event = client.post(
        "/api/do/events",
        json={
            "resourceId": resource["id"],
            "titre": "Intervention",
            "start": "2026-01-01T08:00:00",
            "end": "2026-01-01T10:00:00",
        },
        headers=auth_headers(),
    ).get_json()

    resp = client.delete(f"/api/do/events/{event['id']}", headers=auth_headers())
    assert resp.status_code == 204

    resp = client.get(f"/api/do/events/{event['id']}")
    assert resp.status_code == 404
