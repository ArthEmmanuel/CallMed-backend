from flask import jsonify, request

from services.appointment_service import AppointmentService
from services.directory_service import DirectoryService
from services.matchmaking_service import MatchmakingService
from services.user_service import UserService


class ApiController:
    def __init__(
        self,
        users: UserService,
        directory: DirectoryService,
        appointments: AppointmentService,
        matchmaking: MatchmakingService,
    ):
        self.users = users
        self.directory = directory
        self.appointments = appointments
        self.matchmaking = matchmaking

    @staticmethod
    def health():
        return jsonify({"status": "ok", "message": "AgendaMed API funcionando"})

    @staticmethod
    def healthz():
        return jsonify({"status": "ok", "service": "callmed-api"})

    def login(self):
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("senha", "")).strip()
        if not email or not password:
            return jsonify({"erro": "E-mail e senha são obrigatórios"}), 400
        user = self.users.login(email, password)
        return jsonify(
            {"mensagem": "Login realizado com sucesso", "usuario": user}
        )

    def users_collection(self):
        if request.method == "GET":
            return jsonify(self.users.list_users())

        payload = request.get_json(silent=True) or {}
        user = self.users.create_user(payload)
        return jsonify({"mensagem": "Usuário criado", "usuario": user}), 201

    def user_by_id(self, user_id):
        return jsonify(self.users.get_user(user_id))

    def register(self):
        payload = request.get_json(silent=True) or {}
        user = self.users.create_user(payload, frontend_fields=True)
        return jsonify({"mensagem": "Usuário criado", "usuario": user}), 201

    def profile(self, user_id):
        if request.method == "GET":
            return jsonify(self.users.get_profile(user_id)), 200
        payload = request.get_json(silent=True) or {}
        return jsonify(self.users.update_profile(user_id, payload)), 200

    def doctors_collection(self):
        if request.method == "GET":
            return jsonify(self.directory.list_records("medicos"))
        record, status = self.directory.save_record(
            "medicos", request.get_json(silent=True) or {}, truthy_status=True
        )
        return jsonify(record), status

    def patients_collection(self):
        if request.method == "GET":
            return jsonify(self.directory.list_records("pacientes"))
        record, status = self.directory.save_record(
            "pacientes", request.get_json(silent=True) or {}, truthy_status=True
        )
        return jsonify(record), status

    def doctor_by_id(self, doctor_id):
        if request.method == "DELETE":
            return jsonify(
                self.directory.delete_record("medicos", doctor_id, "Médico")
            )
        return jsonify(self.directory.get_record("medicos", doctor_id, "Médico"))

    def patient_by_id(self, patient_id):
        if request.method == "DELETE":
            return jsonify(
                self.directory.delete_record("pacientes", patient_id, "Paciente")
            )
        return jsonify(
            self.directory.get_record("pacientes", patient_id, "Paciente")
        )

    def clinics_collection(self):
        if request.method == "GET":
            return jsonify(self.directory.list_records("clinicas"))
        clinic, status = self.directory.save_record(
            "clinicas", request.get_json(silent=True) or {}
        )
        return jsonify(clinic), status

    def delete_clinic(self, clinic_id):
        return jsonify(
            self.directory.delete_record(
                "clinicas",
                clinic_id,
                "Clínica",
                response_key="clinica",
                message="Clínica excluída",
            )
        )

    def history_collection(self):
        if request.method == "GET":
            return jsonify(self.directory.list_history())
        item = self.directory.create_history(request.get_json(silent=True) or {})
        return jsonify(item), 201

    def settings(self):
        if request.method == "GET":
            return jsonify(self.directory.get_settings())
        settings = self.directory.update_settings(
            request.get_json(silent=True) or {}
        )
        return jsonify(settings)

    def appointments_collection(self):
        if request.method == "GET":
            return jsonify(self.appointments.list_appointments())
        appointment, status = self.appointments.save_appointment(
            request.get_json(silent=True) or {}
        )
        return jsonify(appointment), status

    def legacy_agenda(self):
        if request.method == "GET":
            return jsonify(self.appointments.list_appointments())
        appointment = self.appointments.create_legacy_appointment(
            request.get_json(silent=True) or {}
        )
        return jsonify(appointment), 201

    def delete_appointment(self, appointment_id):
        return jsonify(self.appointments.delete_appointment(appointment_id))

    def matchmaking_result(self, triage=False):
        payload = request.get_json(silent=True) or {}
        patient_id = payload.get("paciente_id", payload.get("pacienteId"))
        need = str(payload.get("necessidade", "")).strip()
        if not patient_id:
            return jsonify({"erro": "paciente_id é obrigatório"}), 400
        if not need:
            return jsonify({"erro": "necessidade é obrigatória"}), 400

        symptoms = (
            payload.get("sintomas", [])
            if triage
            else payload.get("sintomas", payload.get("sintoma", []))
        )
        result = self.matchmaking.build_response(
            patient_id,
            need,
            symptoms,
            None if triage else payload.get("data"),
            None if triage else payload.get("hora"),
        )
        return jsonify(result), 200

    def doctor_availability(self, doctor_id):
        self.directory.get_doctor_for_availability(doctor_id)
        date = request.args.get("data")
        hours = request.args.getlist("hora")
        return jsonify(self.appointments.get_availability(doctor_id, date, hours))
