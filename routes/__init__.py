from routes.appointment_routes import create_appointment_blueprint
from routes.directory_routes import create_directory_blueprint
from routes.recommendation_routes import create_recommendation_blueprint
from routes.system_routes import create_system_blueprint
from routes.user_routes import create_user_blueprint

__all__ = [
    "create_appointment_blueprint",
    "create_directory_blueprint",
    "create_recommendation_blueprint",
    "create_system_blueprint",
    "create_user_blueprint",
]
