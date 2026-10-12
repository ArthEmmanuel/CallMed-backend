from flask import g, jsonify, request

from services.errors import ServiceError
from services.triage_service import TriageService


class TriageController:
    def __init__(self, triage: TriageService):
        self.triage = triage

    @staticmethod
    def _payload():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ServiceError("O corpo da requisição deve ser um objeto JSON", 400)
        return payload

    def conversations_collection(self):
        if request.method == "GET":
            return jsonify(
                self.triage.list_conversations(g.authenticated_user)
            )
        payload = self._payload()
        conversation = self.triage.create_conversation(
            g.authenticated_user,
            payload.get("pacienteId"),
        )
        return jsonify(conversation), 201

    def conversation_by_id(self, conversation_id):
        actor = g.authenticated_user
        if request.method == "GET":
            return jsonify(
                self.triage.get_conversation(conversation_id, actor)
            )
        if request.method == "PATCH":
            return jsonify(
                self.triage.correct_conversation(
                    conversation_id,
                    self._payload(),
                    actor,
                )
            )
        return jsonify(
            self.triage.delete_conversation(conversation_id, actor)
        )

    def conversation_messages(self, conversation_id):
        payload = self._payload()
        message = payload.get("mensagem", payload.get("message"))
        return jsonify(
            self.triage.send_message(
                conversation_id,
                message,
                g.authenticated_user,
            )
        )
