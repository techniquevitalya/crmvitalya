# crmvitalya — Planning

Application web Flask de gestion de planning (techniciens, interventions,
indisponibilités), conçue comme remplacement complet de PlanningPME :
une interface utilisable directement par le bureau et les techniciens,
plus une API REST pour d'éventuelles intégrations externes.

## Stack

- Flask + Flask-SQLAlchemy (ORM) + Jinja2 (interface web)
- Flask-Login pour l'authentification (comptes admin et technicien)
- Flask-Migrate (Alembic) pour les migrations de schéma
- SQLite par défaut, compatible PostgreSQL via `DATABASE_URL`
- API REST protégée par clé API (header `X-API-Key`) pour les intégrations externes

## Démarrage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # puis éditer SECRET_KEY, API_KEY, DATABASE_URL

flask db upgrade        # crée les tables (technicians, events, users)
python seed.py           # crée un compte admin (admin/admin123) + données de démo

python run.py             # démarre sur http://127.0.0.1:5000
```

Changez immédiatement le mot de passe admin par défaut en production.

## Interface web

| Rôle | Ce qu'il voit |
|---|---|
| **Admin** | `/planning` — planning de tous les techniciens (agenda semaine, filtrable par technicien), création/modification/suppression d'interventions ; `/techniciens` — gestion des techniciens et de leurs identifiants de connexion |
| **Technicien** | `/mon-planning` — son propre agenda semaine, lecture seule |

Chaque technicien a son propre compte (créé par l'admin depuis `/techniciens`)
et ne voit jamais le planning des autres.

## Modèle de données

**Technician** (`technicians`) — un intervenant :
`id, nom, prenom, email, equipe, couleur, actif`

**Event** (`events`) — une intervention ou une indisponibilité,
rattachée à un technicien :
`id, resourceId, titre, description, start, end, isUnavailability, couleur, duration`

`duration` est calculé (non stocké) et renvoyé sous la forme
`{"time": {"hour": H, "minute": M}}`, au même format que l'API PlanningPME
déjà consommée par la webapp Vitalya — pour faciliter une migration
progressive.

## Endpoints

Toutes les routes `GET` sont publiques. Les routes `POST` / `PUT` / `DELETE`
exigent le header `X-API-Key: <API_KEY>`.

### Techniciens

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/resource` | Liste des techniciens (`?actif=true` pour filtrer) |
| GET | `/api/resource/<id>` | Détail d'un technicien |
| POST | `/api/resource` | Créer un technicien (`nom`, `prenom` requis) |
| PUT | `/api/resource/<id>` | Modifier un technicien |
| DELETE | `/api/resource/<id>` | Supprimer un technicien |

### Interventions / indisponibilités

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/do/events` | Liste (`?resourceId=`, `?isUnavailability=`, `?start=`, `?end=`) |
| GET | `/api/do/events/<id>` | Détail d'un événement |
| POST | `/api/do/events` | Créer (`resourceId`, `titre`, `start`, `end` requis, ISO 8601) |
| PUT | `/api/do/events/<id>` | Modifier un événement |
| DELETE | `/api/do/events/<id>` | Supprimer un événement |

### Divers

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/health` | Vérification de disponibilité |

## Tests

```bash
python -m pytest tests/ -v
```

## Migrations

```bash
flask db migrate -m "description du changement"
flask db upgrade
```
