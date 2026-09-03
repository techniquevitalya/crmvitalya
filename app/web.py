from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import admin_required
from app.extensions import db
from app.models import Event, Technician, User

bp = Blueprint("web", __name__)

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def _monday_of(d):
    return d - timedelta(days=d.weekday())


def _week_range(start_param):
    if start_param:
        try:
            start = date.fromisoformat(start_param)
        except ValueError:
            start = _monday_of(date.today())
    else:
        start = _monday_of(date.today())
    start = _monday_of(start)
    days = [start + timedelta(days=i) for i in range(7)]
    return start, days


def _agenda_for(days, technician_id=None):
    week_start = datetime.combine(days[0], datetime.min.time())
    week_end = datetime.combine(days[-1] + timedelta(days=1), datetime.min.time())

    query = Event.query.filter(Event.start >= week_start, Event.start < week_end)
    if technician_id is not None:
        query = query.filter_by(resource_id=technician_id)
    events = query.order_by(Event.start).all()

    agenda = {d: [] for d in days}
    for event in events:
        agenda[event.start.date()].append(event)
    return agenda


@bp.get("/")
@login_required
def index():
    if current_user.is_admin:
        return redirect(url_for("web.planning"))
    return redirect(url_for("web.mon_planning"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("web.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("web.index"))
        flash("Identifiants incorrects.", "error")

    return render_template("login.html")


@bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("web.login"))


@bp.get("/planning")
@login_required
@admin_required
def planning():
    start, days = _week_range(request.args.get("start"))
    technician_id = request.args.get("technicien", type=int)
    agenda = _agenda_for(days, technician_id)

    return render_template(
        "planning.html",
        days=days,
        jours=JOURS,
        agenda=agenda,
        technicians=Technician.query.order_by(Technician.nom).all(),
        selected_technician=technician_id,
        prev_start=(start - timedelta(days=7)).isoformat(),
        next_start=(start + timedelta(days=7)).isoformat(),
        today_start=_monday_of(date.today()).isoformat(),
    )


@bp.get("/mon-planning")
@login_required
def mon_planning():
    if current_user.is_admin or not current_user.technician_id:
        abort(404)

    start, days = _week_range(request.args.get("start"))
    agenda = _agenda_for(days, current_user.technician_id)

    return render_template(
        "mon_planning.html",
        days=days,
        jours=JOURS,
        agenda=agenda,
        prev_start=(start - timedelta(days=7)).isoformat(),
        next_start=(start + timedelta(days=7)).isoformat(),
        today_start=_monday_of(date.today()).isoformat(),
    )


def _parse_event_form(form):
    technician_id = form.get("technicien_id", type=int)
    titre = form.get("titre", "").strip()
    jour = form.get("date", "")
    heure_debut = form.get("heure_debut", "")
    heure_fin = form.get("heure_fin", "")

    errors = []
    if not technician_id or not db.session.get(Technician, technician_id):
        errors.append("Technicien invalide.")
    if not titre:
        errors.append("Le titre est requis.")

    start = end = None
    try:
        start = datetime.fromisoformat(f"{jour}T{heure_debut}")
        end = datetime.fromisoformat(f"{jour}T{heure_fin}")
    except ValueError:
        errors.append("Date ou heure invalide.")

    if start and end and end <= start:
        errors.append("L'heure de fin doit être après l'heure de début.")

    return {
        "technician_id": technician_id,
        "titre": titre,
        "description": form.get("description", "").strip() or None,
        "start": start,
        "end": end,
        "is_unavailability": form.get("is_unavailability") == "on",
    }, errors


@bp.route("/planning/new", methods=["GET", "POST"])
@login_required
@admin_required
def event_new():
    prefill_date = request.args.get("date", date.today().isoformat())
    prefill_start = request.args.get("start", date.today().isoformat())

    if request.method == "POST":
        data, errors = _parse_event_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            event = Event(
                resource_id=data["technician_id"],
                titre=data["titre"],
                description=data["description"],
                start=data["start"],
                end=data["end"],
                is_unavailability=data["is_unavailability"],
            )
            db.session.add(event)
            db.session.commit()
            flash("Intervention créée.", "success")
            return redirect(
                url_for("web.planning", start=_monday_of(data["start"].date()).isoformat())
            )

    return render_template(
        "event_form.html",
        event=None,
        technicians=Technician.query.filter_by(actif=True).order_by(Technician.nom).all(),
        prefill_date=prefill_date,
        back_start=prefill_start,
    )


@bp.route("/planning/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def event_edit(event_id):
    event = Event.query.get_or_404(event_id)

    if request.method == "POST":
        data, errors = _parse_event_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            event.resource_id = data["technician_id"]
            event.titre = data["titre"]
            event.description = data["description"]
            event.start = data["start"]
            event.end = data["end"]
            event.is_unavailability = data["is_unavailability"]
            db.session.commit()
            flash("Intervention modifiée.", "success")
            return redirect(
                url_for("web.planning", start=_monday_of(data["start"].date()).isoformat())
            )

    return render_template(
        "event_form.html",
        event=event,
        technicians=Technician.query.filter_by(actif=True).order_by(Technician.nom).all(),
        prefill_date=event.start.date().isoformat(),
        back_start=_monday_of(event.start.date()).isoformat(),
    )


@bp.post("/planning/<int:event_id>/delete")
@login_required
@admin_required
def event_delete(event_id):
    event = Event.query.get_or_404(event_id)
    week_start = _monday_of(event.start.date()).isoformat()
    db.session.delete(event)
    db.session.commit()
    flash("Intervention supprimée.", "success")
    return redirect(url_for("web.planning", start=week_start))


@bp.get("/techniciens")
@login_required
@admin_required
def technicians():
    return render_template(
        "technicians.html", technicians=Technician.query.order_by(Technician.nom).all()
    )


@bp.post("/techniciens/new")
@login_required
@admin_required
def technician_new():
    nom = request.form.get("nom", "").strip()
    prenom = request.form.get("prenom", "").strip()
    if not nom or not prenom:
        flash("Nom et prénom sont requis.", "error")
        return redirect(url_for("web.technicians"))

    technician = Technician(
        nom=nom,
        prenom=prenom,
        email=request.form.get("email", "").strip() or None,
        equipe=request.form.get("equipe", "").strip() or None,
    )
    db.session.add(technician)
    db.session.commit()
    flash(f"Technicien {prenom} {nom} créé.", "success")
    return redirect(url_for("web.technicians"))


@bp.post("/techniciens/<int:technician_id>/edit")
@login_required
@admin_required
def technician_edit(technician_id):
    technician = Technician.query.get_or_404(technician_id)
    technician.nom = request.form.get("nom", technician.nom).strip()
    technician.prenom = request.form.get("prenom", technician.prenom).strip()
    technician.email = request.form.get("email", "").strip() or None
    technician.equipe = request.form.get("equipe", "").strip() or None
    db.session.commit()
    flash("Technicien mis à jour.", "success")
    return redirect(url_for("web.technicians"))


@bp.post("/techniciens/<int:technician_id>/toggle-actif")
@login_required
@admin_required
def technician_toggle_actif(technician_id):
    technician = Technician.query.get_or_404(technician_id)
    technician.actif = not technician.actif
    db.session.commit()
    return redirect(url_for("web.technicians"))


@bp.post("/techniciens/<int:technician_id>/compte")
@login_required
@admin_required
def technician_account(technician_id):
    technician = Technician.query.get_or_404(technician_id)
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Identifiant et mot de passe sont requis.", "error")
        return redirect(url_for("web.technicians"))

    user = technician.user
    if user is None:
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash("Cet identifiant est déjà utilisé.", "error")
            return redirect(url_for("web.technicians"))
        user = User(username=username, role="technicien", technician_id=technician.id)
    else:
        if username != user.username and User.query.filter_by(username=username).first():
            flash("Cet identifiant est déjà utilisé.", "error")
            return redirect(url_for("web.technicians"))
        user.username = username

    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"Identifiants définis pour {technician.prenom} {technician.nom}.", "success")
    return redirect(url_for("web.technicians"))
