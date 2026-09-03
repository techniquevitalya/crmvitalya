import pytest

from app import create_app
from app.extensions import db
from app.models import Technician, User


class TestConfig:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_KEY = "test-key"
    WTF_CSRF_ENABLED = False


@pytest.fixture
def app():
    app = create_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()

        admin = User(username="admin", role="admin")
        admin.set_password("admin123")

        alice = Technician(nom="Dupont", prenom="Alice")
        db.session.add_all([admin, alice])
        db.session.commit()

        alice_user = User(username="alice", role="technicien", technician_id=alice.id)
        alice_user.set_password("alice123")
        db.session.add(alice_user)
        db.session.commit()

        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post(
        "/login", data={"username": username, "password": password}, follow_redirects=True
    )


def test_anonymous_redirected_to_login(client):
    resp = client.get("/planning", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_wrong_password(client):
    resp = login(client, "admin", "wrong")
    assert b"Identifiants incorrects" in resp.data


def test_admin_login_redirects_to_planning(client):
    resp = login(client, "admin", "admin123")
    assert resp.status_code == 200
    assert b"Planning" in resp.data


def test_technicien_login_redirects_to_own_planning(client):
    resp = login(client, "alice", "alice123")
    assert resp.status_code == 200
    assert b"Mon planning" in resp.data


def test_technicien_cannot_reach_admin_pages(client, app):
    login(client, "alice", "alice123")

    resp = client.get("/techniciens", follow_redirects=True)
    assert b"Ajouter un technicien" not in resp.data

    resp = client.get("/planning", follow_redirects=True)
    assert b"Nouvelle intervention" not in resp.data


def test_admin_creates_event_and_technician_sees_only_own(client, app):
    login(client, "admin", "admin123")

    with app.app_context():
        alice_id = Technician.query.filter_by(nom="Dupont").first().id
        bob = Technician(nom="Martin", prenom="Bob")
        db.session.add(bob)
        db.session.commit()
        bob_id = bob.id
        bob_user = User(username="bob", role="technicien", technician_id=bob_id)
        bob_user.set_password("bob123")
        db.session.add(bob_user)
        db.session.commit()

    resp = client.post(
        "/planning/new",
        data={
            "technicien_id": alice_id,
            "titre": "Intervention Alice",
            "description": "",
            "date": "2026-09-07",
            "heure_debut": "09:00",
            "heure_fin": "11:00",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Intervention Alice" in resp.data

    client.get("/logout")
    login(client, "bob", "bob123")
    resp = client.get("/mon-planning", query_string={"start": "2026-09-07"})
    assert b"Intervention Alice" not in resp.data

    client.get("/logout")
    login(client, "alice", "alice123")
    resp = client.get("/mon-planning", query_string={"start": "2026-09-07"})
    assert b"Intervention Alice" in resp.data


def test_event_end_before_start_rejected(client, app):
    login(client, "admin", "admin123")
    with app.app_context():
        alice_id = Technician.query.filter_by(nom="Dupont").first().id

    resp = client.post(
        "/planning/new",
        data={
            "technicien_id": alice_id,
            "titre": "Invalide",
            "description": "",
            "date": "2026-09-07",
            "heure_debut": "11:00",
            "heure_fin": "09:00",
        },
        follow_redirects=True,
    )
    assert "doit être après".encode() in resp.data


def test_admin_creates_technician_account(client, app):
    login(client, "admin", "admin123")
    with app.app_context():
        alice_id = Technician.query.filter_by(nom="Dupont").first().id

    resp = client.post(
        f"/techniciens/{alice_id}/compte",
        data={"username": "alice2", "password": "newpass123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    client.get("/logout")
    resp = login(client, "alice2", "newpass123")
    assert b"Mon planning" in resp.data
