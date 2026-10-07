from flask import Blueprint


def create_system_blueprint(controller):
    blueprint = Blueprint("system", __name__)
    blueprint.add_url_rule("/api/health", "health", controller.health, methods=["GET"])
    blueprint.add_url_rule(
        "/api/healthz", "healthz", controller.healthz, methods=["GET"]
    )
    return blueprint
