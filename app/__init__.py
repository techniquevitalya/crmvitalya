from flask import Flask, jsonify

from app.extensions import db, migrate


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.api.resources import bp as resources_bp
    from app.api.events import bp as events_bp

    app.register_blueprint(resources_bp)
    app.register_blueprint(events_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "not found"}), 404

    return app
