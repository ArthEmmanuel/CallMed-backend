from flask import Blueprint

from auth import admin_required, token_required


def create_user_blueprint(controller):
    blueprint = Blueprint("users", __name__)
    blueprint.add_url_rule("/api/login", "login", controller.login, methods=["POST"])
    blueprint.add_url_rule(
        "/api/usuarios",
        "users_collection",
        admin_required(controller.users_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/usuarios/<string:user_id>",
        "user_by_id",
        token_required(controller.user_by_id),
        methods=["GET", "PUT", "PATCH", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/administradores",
        "admins_collection",
        admin_required(controller.admins_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/administradores/<string:admin_id>",
        "admin_by_id",
        admin_required(controller.admin_by_id),
        methods=["GET", "PUT", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/cadastro", "register", controller.register, methods=["POST"]
    )
    blueprint.add_url_rule(
        "/api/perfil/<string:user_id>",
        "profile",
        token_required(controller.profile),
        methods=["GET", "PUT"],
    )
    return blueprint
