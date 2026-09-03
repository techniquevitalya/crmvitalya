from flask import Flask, jsonify

from app.extensions import db, login_manager, migrate


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "web.login"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.api.resources import bp as resources_bp
    from app.api.events import bp as events_bp
    from app.web import bp as web_bp

    app.register_blueprint(resources_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(web_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "not found"}), 404

    return app
