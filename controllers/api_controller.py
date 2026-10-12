from flask import g, jsonify, request

from services.appointment_service import AppointmentService
from services.auth_service import AuthService
from services.directory_service import DirectoryService
from services.errors import ServiceError
from services.matchmaking_service import MatchmakingService
from services.user_service import UserService


class ApiController:
    def __init__(
        self,
        users: UserService,
        directory: DirectoryService,
        appointments: AppointmentService,
        matchmaking: MatchmakingService,
        auth: AuthService,
    ):
        self.users = users
        self.directory = directory
        self.appointments = appointments
        self.matchmaking = matchmaking
        self.auth = auth

    @staticmethod
    def health():
        return jsonify({"status": "ok", "message": "AgendaMed API funcionando"})

    @staticmethod
    def healthz():
        return jsonify({"status": "ok", "service": "callmed-api"})

    @staticmethod
    def _payload():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ServiceError("O corpo da requisição deve ser um objeto JSON", 400)
        return payload

    def login(self):
        payload = self._payload()
        email = payload.get("email")
        password = payload.get("senha")
        if not email or not password:
            raise ServiceError("E-mail e senha são obrigatórios", 400)
        return jsonify(self.auth.login(email, password))

    def users_collection(self):
        if request.method == "GET":
            return jsonify(self.users.list_users(g.authenticated_user))

        payload = self._payload()
        user = self.users.create_user(payload)
        return jsonify({"mensagem": "Usuário criado", "usuario": user}), 201

    def user_by_id(self, user_id):
        if request.method == "GET":
            return jsonify(self.users.get_user(user_id, g.authenticated_user))
        if request.method in {"PUT", "PATCH"}:
            user = self.users.update_user(
                user_id,
                self._payload(),
                g.authenticated_user,
            )
            return jsonify(user)
        return jsonify(self.users.delete_user(user_id, g.authenticated_user))

    def admins_collection(self):
        if request.method == "GET":
            return jsonify(self.users.list_admins(g.authenticated_user))
        admin = self.users.create_admin(self._payload())
        return jsonify(
            {"mensagem": "Administrador criado", "administrador": admin}
        ), 201

    def admin_by_id(self, admin_id):
        if request.method == "GET":
            return jsonify(self.users.get_admin(admin_id, g.authenticated_user))
        if request.method == "PUT":
            admin = self.users.update_admin(admin_id, self._payload())
            return jsonify(admin)
        return jsonify(self.users.delete_admin(admin_id))

    def register(self):
        user = self.users.create_user(
            self._payload(),
            frontend_fields=True,
            public_registration=True,
        )
        return jsonify({"mensagem": "Usuário criado", "usuario": user}), 201

    def profile(self, user_id):
        if request.method == "GET":
            return jsonify(
                self.users.get_profile(user_id, g.authenticated_user)
            ), 200
        return jsonify(
            self.users.update_profile(
                user_id,
                self._payload(),
                g.authenticated_user,
            )
        ), 200

    def doctors_collection(self):
        if request.method == "GET":
            return jsonify(
                self.directory.list_records("medicos", g.authenticated_user)
            )
        record, status = self.directory.save_record(
            "medicos",
            self._payload(),
            g.authenticated_user,
            truthy_status=True,
        )
        return jsonify(record), status

    def patients_collection(self):
        if request.method == "GET":
            return jsonify(
                self.directory.list_records("pacientes", g.authenticated_user)
            )
        record, status = self.directory.save_record(
            "pacientes",
            self._payload(),
            g.authenticated_user,
            truthy_status=True,
        )
        return jsonify(record), status

    def doctor_by_id(self, doctor_id):
        actor = g.authenticated_user
        if request.method == "DELETE":
            return jsonify(
                self.directory.delete_record(
                    "medicos", doctor_id, "Médico", actor=actor
                )
            )
        if request.method == "PUT":
            return jsonify(
                self.directory.update_record(
                    "medicos",
                    doctor_id,
                    self._payload(),
                    "Médico",
                    actor,
                )
            )
        return jsonify(
            self.directory.get_record(
                "medicos", doctor_id, "Médico", actor, read=True
            )
        )

    def patient_by_id(self, patient_id):
        actor = g.authenticated_user
        if request.method == "DELETE":
            return jsonify(
                self.directory.delete_record(
                    "pacientes", patient_id, "Paciente", actor=actor
                )
            )
        if request.method == "PUT":
            return jsonify(
                self.directory.update_record(
                    "pacientes",
                    patient_id,
                    self._payload(),
                    "Paciente",
                    actor,
                )
            )
        return jsonify(
            self.directory.get_record(
                "pacientes", patient_id, "Paciente", actor, read=True
            )
        )

    def clinics_collection(self):
        if request.method == "GET":
            return jsonify(
                self.directory.list_records("clinicas", g.authenticated_user)
            )
        clinic, status = self.directory.save_record(
            "clinicas", self._payload(), g.authenticated_user
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
                actor=g.authenticated_user,
            )
        )

    def clinic_by_id(self, clinic_id):
        actor = g.authenticated_user
        if request.method == "GET":
            return jsonify(
                self.directory.get_record(
                    "clinicas", clinic_id, "Clínica", actor, read=True
                )
            )
        if request.method in {"PUT", "PATCH"}:
            return jsonify(
                self.directory.update_record(
                    "clinicas",
                    clinic_id,
                    self._payload(),
                    "Clínica",
                    actor,
                )
            )
        return jsonify(
            self.directory.delete_record(
                "clinicas",
                clinic_id,
                "Clínica",
                response_key="clinica",
                message="Clínica excluída",
                actor=actor,
            )
        )

    def specialties_collection(self):
        if request.method == "GET":
            return jsonify(
                self.directory.list_records(
                    "especialidades", g.authenticated_user
                )
            )
        record, status = self.directory.save_record(
            "especialidades",
            self._payload(),
            g.authenticated_user,
        )
        return jsonify(record), status

    def specialty_by_id(self, specialty_id):
        actor = g.authenticated_user
        if request.method == "GET":
            return jsonify(
                self.directory.get_record(
                    "especialidades",
                    specialty_id,
                    "Especialidade",
                    actor,
                    read=True,
                )
            )
        if request.method in {"PUT", "PATCH"}:
            return jsonify(
                self.directory.update_record(
                    "especialidades",
                    specialty_id,
                    self._payload(),
                    "Especialidade",
                    actor,
                )
            )
        return jsonify(
            self.directory.delete_record(
                "especialidades",
                specialty_id,
                "Especialidade",
                actor=actor,
            )
        )

    def history_collection(self):
        if request.method == "GET":
            return jsonify(self.directory.list_history(g.authenticated_user))
        item = self.directory.create_history(
            self._payload(), g.authenticated_user
        )
        return jsonify(item), 201

    def history_by_id(self, history_id):
        actor = g.authenticated_user
        if request.method == "GET":
            return jsonify(self.directory.get_history(history_id, actor))
        if request.method in {"PUT", "PATCH"}:
            return jsonify(
                self.directory.update_history(
                    history_id,
                    self._payload(),
                    actor,
                )
            )
        return jsonify(self.directory.delete_history(history_id, actor))

    def settings(self):
        if request.method == "GET":
            return jsonify(self.directory.get_settings(g.authenticated_user))
        if request.method == "DELETE":
            return jsonify(self.directory.delete_settings(g.authenticated_user))
        if request.method == "PUT":
            settings = self.directory.replace_settings(
                self._payload(), g.authenticated_user
            )
            return jsonify(settings)
        settings = self.directory.update_settings(
            self._payload(), g.authenticated_user
        )
        return jsonify(settings)

    def user_settings_collection(self):
        if request.method == "GET":
            return jsonify(
                self.directory.list_user_settings(g.authenticated_user)
            )
        setting = self.directory.create_user_setting(
            self._payload(), g.authenticated_user
        )
        return jsonify(setting), 201

    def user_setting_by_id(self, setting_id):
        actor = g.authenticated_user
        if request.method == "GET":
            return jsonify(self.directory.get_user_setting(setting_id, actor))
        if request.method in {"PUT", "PATCH"}:
            return jsonify(
                self.directory.update_user_setting(
                    setting_id,
                    self._payload(),
                    actor,
                )
            )
        return jsonify(
            self.directory.delete_user_setting(setting_id, actor)
        )

    def appointments_collection(self):
        if request.method == "GET":
            return jsonify(
                self.appointments.list_appointments_for(g.authenticated_user)
            )
        appointment, status = self.appointments.save_appointment(
            self._payload(), actor=g.authenticated_user
        )
        return jsonify(appointment), status

    def appointment_by_id(self, appointment_id):
        if request.method == "GET":
            return jsonify(
                self.appointments.get_appointment(
                    appointment_id, g.authenticated_user
                )
            )
        if request.method == "PUT":
            appointment, status = self.appointments.save_appointment(
                self._payload(),
                appointment_id=appointment_id,
                require_existing=True,
                actor=g.authenticated_user,
            )
            return jsonify(appointment), status
        return jsonify(
            self.appointments.delete_appointment(
                appointment_id, g.authenticated_user
            )
        )

    def legacy_agenda(self):
        if request.method == "GET":
            return jsonify(
                self.appointments.list_appointments_for(g.authenticated_user)
            )
        appointment = self.appointments.create_legacy_appointment(
            self._payload(), g.authenticated_user
        )
        return jsonify(appointment), 201

    def delete_appointment(self, appointment_id):
        return jsonify(
            self.appointments.delete_appointment(
                appointment_id, g.authenticated_user
            )
        )

    def matchmaking_result(self, triage=False):
        payload = self._payload()
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
            actor=g.authenticated_user,
        )
        return jsonify(result), 200

    def doctor_availability(self, doctor_id):
        self.directory.get_doctor_for_availability(
            doctor_id, g.authenticated_user
        )
        date = request.args.get("data")
        hours = request.args.getlist("hora")
        return jsonify(self.appointments.get_availability(doctor_id, date, hours))
