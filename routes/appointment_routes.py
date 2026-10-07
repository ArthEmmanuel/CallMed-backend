from flask import Blueprint


def create_appointment_blueprint(controller):
    blueprint = Blueprint("appointments", __name__)
    blueprint.add_url_rule(
        "/api/agendamentos",
        "appointments_collection",
        controller.appointments_collection,
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/agenda",
        "legacy_agenda",
        controller.legacy_agenda,
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/agenda/<int:appointment_id>",
        "delete_appointment",
        controller.delete_appointment,
        methods=["DELETE"],
    )
    return blueprint
