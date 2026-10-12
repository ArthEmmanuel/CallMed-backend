from flask import Blueprint

from auth import token_required


def create_triage_blueprint(controller):
    blueprint = Blueprint("triage_conversations", __name__)
    blueprint.add_url_rule(
        "/api/triagem/conversas",
        "conversations_collection",
        token_required(controller.conversations_collection),
        methods=["GET", "POST"],
    )
    blueprint.add_url_rule(
        "/api/triagem/conversas/<string:conversation_id>",
        "conversation_by_id",
        token_required(controller.conversation_by_id),
        methods=["GET", "PATCH", "DELETE"],
    )
    blueprint.add_url_rule(
        "/api/triagem/conversas/<string:conversation_id>/mensagens",
        "conversation_messages",
        token_required(controller.conversation_messages),
        methods=["POST"],
    )
    return blueprint
