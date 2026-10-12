from flask import Blueprint

from auth import admin_required, token_required


def create_directory_blueprint(controller):
    blueprint = Blueprint("directory", __name__)
    blueprint.add_url_rule(
        "/api/medicos",
        "doctors_collection",
        token_required(controller.doctors_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/medicos/<string:doctor_id>",
        "doctor_by_id",
        token_required(controller.doctor_by_id),
        methods=["GET", "PUT", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/pacientes",
        "patients_collection",
        token_required(controller.patients_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/pacientes/<string:patient_id>",
        "patient_by_id",
        token_required(controller.patient_by_id),
        methods=["GET", "PUT", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/clinicas",
        "clinics_collection",
        admin_required(controller.clinics_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/clinicas/<string:clinic_id>",
        "clinic_by_id",
        admin_required(controller.clinic_by_id),
        methods=["GET", "PUT", "PATCH", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/especialidades",
        "specialties_collection",
        token_required(controller.specialties_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/especialidades/<string:specialty_id>",
        "specialty_by_id",
        token_required(controller.specialty_by_id),
        methods=["GET", "PUT", "PATCH", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/historico",
        "history_collection",
        admin_required(controller.history_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/historico/<string:history_id>",
        "history_by_id",
        admin_required(controller.history_by_id),
        methods=["GET", "PUT", "PATCH", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/config",
        "settings",
        admin_required(controller.settings),
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/configuracoes-usuario",
        "user_settings_collection",
        token_required(controller.user_settings_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/configuracoes-usuario/<string:setting_id>",
        "user_setting_by_id",
        token_required(controller.user_setting_by_id),
        methods=["GET", "PUT", "PATCH", "DELETE"],
    )
    return blueprint
