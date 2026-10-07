from flask import Blueprint


def create_user_blueprint(controller):
    blueprint = Blueprint("users", __name__)
    blueprint.add_url_rule("/api/login", "login", controller.login, methods=["POST"])
    blueprint.add_url_rule(
        "/api/usuarios",
        "users_collection",
        controller.users_collection,
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/usuarios/<int:user_id>",
        "user_by_id",
        controller.user_by_id,
        methods=["GET"],
    )
    blueprint.add_url_rule(
        "/api/cadastro", "register", controller.register, methods=["POST"]
    )
    blueprint.add_url_rule(
        "/api/perfil/<int:user_id>",
        "profile",
        controller.profile,
        methods=["GET", "PUT"],
    )
    return blueprint
