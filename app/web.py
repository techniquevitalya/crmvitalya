from datetime import date, datetime, timedelta

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import admin_required
from app.extensions import db
from app.models import Event, Technician, User

bp = Blueprint("web", __name__)

JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
VUES = ("jour", "semaine", "mois")

COULEURS = [
    ("", "Standard"),
    ("#007AFF", "Bleu"),
    ("#34c759", "Vert"),
    ("#ff9500", "Orange"),
    ("#af52de", "Violet"),
    ("#30b0c7", "Turquoise"),
    ("#ff3b30", "Rouge"),
]


def _monday_of(d):
    return d - timedelta(days=d.weekday())


def _compute_days(view, start_param):
    try:
        ref = date.fromisoformat(start_param) if start_param else date.today()
    except ValueError:
        ref = date.today()

    if view == "jour":
        days = [ref]
        prev_ref = ref - timedelta(days=1)
        next_ref = ref + timedelta(days=1)
    elif view == "mois":
        first = ref.replace(day=1)
        next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        days = [first + timedelta(days=i) for i in range((next_month - first).days)]
        prev_ref = (first - timedelta(days=1)).replace(day=1)
        next_ref = next_month
    else:
        monday = _monday_of(ref)
        days = [monday + timedelta(days=i) for i in range(7)]
        prev_ref = monday - timedelta(days=7)
        next_ref = monday + timedelta(days=7)

    return days, prev_ref, next_ref


def _agenda_grid(days, technicians):
    day_start = datetime.combine(days[0], datetime.min.time())
    day_end = datetime.combine(days[-1] + timedelta(days=1), datetime.min.time())
    tech_ids = [t.id for t in technicians]

    events = []
    if tech_ids:
        events = (
            Event.query.filter(
                Event.start >= day_start,
                Event.start < day_end,
                Event.resource_id.in_(tech_ids),
            )
            .order_by(Event.start)
            .all()
        )

    grid = {t.id: {d: [] for d in days} for t in technicians}
    for e in events:
        d = e.start.date()
        if e.resource_id in grid and d in grid[e.resource_id]:
            grid[e.resource_id][d].append(e)
    return grid


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
    view = request.args.get("view", "semaine")
    if view not in VUES:
        view = "semaine"
    days, prev_ref, next_ref = _compute_days(view, request.args.get("start"))

    technician_id = request.args.get("technicien", type=int)
    technicians = Technician.query.filter_by(actif=True).order_by(Technician.nom).all()
    if technician_id:
        technicians = [t for t in technicians if t.id == technician_id]

    grid = _agenda_grid(days, technicians)

    return render_template(
        "planning.html",
        editable=True,
        view=view,
        days=days,
        jours=JOURS,
        grid=grid,
        technicians=technicians,
        all_technicians=Technician.query.order_by(Technician.nom).all(),
        selected_technician=technician_id,
        prev_start=prev_ref.isoformat(),
        next_start=next_ref.isoformat(),
        today_start=date.today().isoformat(),
        today=date.today(),
    )


@bp.get("/mon-planning")
@login_required
def mon_planning():
    if current_user.is_admin or not current_user.technician_id:
        abort(404)

    view = request.args.get("view", "semaine")
    if view not in VUES:
        view = "semaine"
    days, prev_ref, next_ref = _compute_days(view, request.args.get("start"))

    technicians = [current_user.technician]
    grid = _agenda_grid(days, technicians)

    return render_template(
        "mon_planning.html",
        editable=False,
        view=view,
        days=days,
        jours=JOURS,
        grid=grid,
        technicians=technicians,
        prev_start=prev_ref.isoformat(),
        next_start=next_ref.isoformat(),
        today_start=date.today().isoformat(),
        today=date.today(),
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
        "couleur": form.get("couleur") or None,
    }, errors


@bp.route("/planning/new", methods=["GET", "POST"])
@login_required
@admin_required
def event_new():
    prefill_date = request.args.get("date", date.today().isoformat())
    prefill_technicien = request.args.get("technicien_id", type=int)
    back_start = request.args.get("start", date.today().isoformat())
    back_view = request.args.get("view", "semaine")

    if request.method == "POST":
        data, errors = _parse_event_form(request.form)
        back_view = request.form.get("view", back_view)
        back_start = request.form.get("back_start", back_start)
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
                couleur=data["couleur"],
            )
            db.session.add(event)
            db.session.commit()
            flash("Intervention créée.", "success")
            return redirect(
                url_for("web.planning", start=back_start, view=back_view)
            )

    return render_template(
        "event_form.html",
        event=None,
        technicians=Technician.query.filter_by(actif=True).order_by(Technician.nom).all(),
        couleurs=COULEURS,
        prefill_date=prefill_date,
        prefill_technicien=prefill_technicien,
        back_start=back_start,
        back_view=back_view,
    )


@bp.route("/planning/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def event_edit(event_id):
    event = Event.query.get_or_404(event_id)
    back_start = request.args.get("start", _monday_of(event.start.date()).isoformat())
    back_view = request.args.get("view", "semaine")

    if request.method == "POST":
        data, errors = _parse_event_form(request.form)
        back_view = request.form.get("view", back_view)
        back_start = request.form.get("back_start", back_start)
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
            event.couleur = data["couleur"]
            db.session.commit()
            flash("Intervention modifiée.", "success")
            return redirect(url_for("web.planning", start=back_start, view=back_view))

    return render_template(
        "event_form.html",
        event=event,
        technicians=Technician.query.filter_by(actif=True).order_by(Technician.nom).all(),
        couleurs=COULEURS,
        prefill_date=event.start.date().isoformat(),
        prefill_technicien=event.resource_id,
        back_start=back_start,
        back_view=back_view,
    )


@bp.post("/planning/<int:event_id>/delete")
@login_required
@admin_required
def event_delete(event_id):
    event = Event.query.get_or_404(event_id)
    back_start = request.form.get("back_start", _monday_of(event.start.date()).isoformat())
    back_view = request.form.get("back_view", "semaine")
    db.session.delete(event)
    db.session.commit()
    flash("Intervention supprimée.", "success")
    return redirect(url_for("web.planning", start=back_start, view=back_view))


@bp.post("/planning/event/<int:event_id>/move")
@login_required
@admin_required
def event_move(event_id):
    event = Event.query.get_or_404(event_id)
    payload = request.get_json(silent=True) or {}

    new_date_str = payload.get("date")
    new_technician_id = payload.get("technicienId")

    if new_technician_id is not None:
        if not db.session.get(Technician, new_technician_id):
            return jsonify({"error": "technicien inconnu"}), 400
        event.resource_id = new_technician_id

    if new_date_str:
        try:
            new_date = date.fromisoformat(new_date_str)
        except ValueError:
            return jsonify({"error": "date invalide"}), 400
        day_shift = new_date - event.start.date()
        event.start += day_shift
        event.end += day_shift

    db.session.commit()
    return jsonify(event.to_dict())


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
