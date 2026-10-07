from flask import Flask, jsonify
from flask_cors import CORS

from config import load_config
from controllers import ApiController
from repositories import MongoRepository
from routes import (
    create_appointment_blueprint,
    create_directory_blueprint,
    create_recommendation_blueprint,
    create_system_blueprint,
    create_user_blueprint,
)
from services import (
    AppointmentService,
    DirectoryService,
    MatchmakingService,
    UserService,
)
from services.errors import ServiceError


def create_app(config_overrides=None, repository=None):
    app = Flask(__name__)
    app.config.update(load_config())
    if config_overrides:
        app.config.update(config_overrides)

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
    )

    data_repository = repository or MongoRepository(
        app.config["MONGO_URI"],
        app.config["DB_NAME"],
    )
    appointments = AppointmentService(data_repository)
    controller = ApiController(
        users=UserService(data_repository),
        directory=DirectoryService(data_repository),
        appointments=appointments,
        matchmaking=MatchmakingService(data_repository, appointments),
    )

    app.register_blueprint(create_system_blueprint(controller))
    app.register_blueprint(create_user_blueprint(controller))
    app.register_blueprint(create_directory_blueprint(controller))
    app.register_blueprint(create_appointment_blueprint(controller))
    app.register_blueprint(create_recommendation_blueprint(controller))

    @app.errorhandler(ServiceError)
    def handle_service_error(error):
        return jsonify({"erro": str(error)}), error.status_code

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=app.config["API_HOST"],
        port=app.config["API_PORT"],
        debug=app.config["DEBUG"],
    )
