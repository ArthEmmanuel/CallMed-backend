from flask import Blueprint


def create_directory_blueprint(controller):
    blueprint = Blueprint("directory", __name__)
    blueprint.add_url_rule(
        "/api/medicos",
        "doctors_collection",
        controller.doctors_collection,
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/medicos/<int:doctor_id>",
        "doctor_by_id",
        controller.doctor_by_id,
        methods=["GET", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/pacientes",
        "patients_collection",
        controller.patients_collection,
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/pacientes/<int:patient_id>",
        "patient_by_id",
        controller.patient_by_id,
        methods=["GET", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/clinicas",
        "clinics_collection",
        controller.clinics_collection,
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/clinicas/<int:clinic_id>",
        "delete_clinic",
        controller.delete_clinic,
        methods=["DELETE"],
    )
    blueprint.add_url_rule(
        "/api/historico",
        "history_collection",
        controller.history_collection,
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/config", "settings", controller.settings, methods=["GET", "POST"]
    )
    return blueprint
