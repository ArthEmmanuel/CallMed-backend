from flask import Blueprint

from auth import token_required


def create_recommendation_blueprint(controller):
    blueprint = Blueprint("recommendations", __name__)
    blueprint.add_url_rule(
        "/api/matchmaking",
        "matchmaking",
        token_required(controller.matchmaking_result),
        defaults={"triage": False},
        methods=["POST"],
    )
    blueprint.add_url_rule(
        "/api/triagem",
        "triage",
        token_required(controller.matchmaking_result),
        defaults={"triage": True},
        methods=["POST"],
    )
    blueprint.add_url_rule(
        "/api/medicos/<int:doctor_id>/disponibilidade",
        "doctor_availability",
        token_required(controller.doctor_availability),
        methods=["GET"],
    )
    return blueprint
