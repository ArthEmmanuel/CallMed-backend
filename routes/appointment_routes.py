from flask import Blueprint

from auth import token_required


def create_appointment_blueprint(controller):
    blueprint = Blueprint("appointments", __name__)
    blueprint.add_url_rule(
        "/api/agendamentos",
        "appointments_collection",
        token_required(controller.appointments_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/agendamentos/<int:appointment_id>",
        "appointment_by_id",
        token_required(controller.appointment_by_id),
        methods=["GET", "PUT", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/agenda",
        "legacy_agenda",
        token_required(controller.legacy_agenda),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/agenda/<int:appointment_id>",
        "delete_appointment",
        token_required(controller.delete_appointment),
        methods=["DELETE"],
    )
    return blueprint
