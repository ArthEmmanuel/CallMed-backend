from flask import Flask, jsonify
from flask_cors import CORS

from config import load_config
from controllers import ApiController
from controllers import TriageController
from repositories import MongoRepository
from repositories.database_module import load_database_module
from routes import (
    create_appointment_blueprint,
    create_directory_blueprint,
    create_recommendation_blueprint,
    create_system_blueprint,
    create_triage_blueprint,
    create_user_blueprint,
)
from services import (
    AppointmentService,
    AuthService,
    DirectoryService,
    MatchmakingService,
    TriageService,
    UserService,
)
from services.errors import ServiceError


def create_app(config_overrides=None, repository=None):
    app = Flask(__name__)
    app.config.update(load_config())
    if config_overrides:
        app.config.update(config_overrides)
    app.config["SECRET_KEY"] = app.config.get("SECRET_KEY")
    if not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "SECRET_KEY não definida. Configure uma chave forte no .env do backend."
        )

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": app.config["CORS_ORIGINS"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )

    data_repository = repository or MongoRepository(
        load_database_module(
            app.config["DATABASE_PROJECT_PATH"],
            app.config["MONGO_URI"],
            app.config["DB_NAME"],
        )
    )
    appointments = AppointmentService(data_repository)
    users = UserService(data_repository)
    auth = AuthService(
        users,
        app.config["SECRET_KEY"],
        app.config["TOKEN_MAX_AGE_SECONDS"],
    )
    app.extensions["auth_service"] = auth
    controller = ApiController(
        users=users,
        directory=DirectoryService(data_repository),
        appointments=appointments,
        matchmaking=MatchmakingService(data_repository, appointments),
        auth=auth,
    )
    triage_controller = TriageController(TriageService(data_repository))

    app.register_blueprint(create_system_blueprint(controller))
    app.register_blueprint(create_user_blueprint(controller))
    app.register_blueprint(create_directory_blueprint(controller))
    app.register_blueprint(create_appointment_blueprint(controller))
    app.register_blueprint(create_recommendation_blueprint(controller))
    app.register_blueprint(create_triage_blueprint(triage_controller))

    @app.errorhandler(ServiceError)
    def handle_service_error(error):
        return jsonify({"erro": str(error)}), error.status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({"erro": "Recurso não encontrado"}), error.code or 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({"erro": "Método não permitido"}), error.code or 405

    @app.errorhandler(500)
    def handle_internal_error(error):
        app.logger.error("Unhandled server error: %s", error)
        return jsonify({"erro": "Erro interno do servidor"}), error.code or 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=app.config["API_HOST"],
        port=app.config["API_PORT"],
        debug=app.config["DEBUG"],
    )
