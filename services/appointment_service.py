from repositories.data_repository import DataRepository
from services.errors import ServiceError
from services.helpers import as_id, normalize_appointment, normalize_text


DEFAULT_SLOTS = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"]


class AppointmentService:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    def list_appointments(self):
        records = self.repository.get_all("agendamentos")
        return [normalize_appointment(item) for item in records]

    def save_appointment(self, payload, appointment_id=None, require_existing=False):
        records = self.repository.get_all("agendamentos")
        appointment = dict(payload)

        aliases = {
            "pacienteId": "paciente_id",
            "medicoId": "medico_id",
            "pacienteNome": "paciente_nome",
            "medicoNome": "medico_nome",
            "medicoEspecialidade": "medico_especialidade",
        }
        for camel_key, snake_key in aliases.items():
            if camel_key in appointment and snake_key not in appointment:
                appointment[snake_key] = appointment[camel_key]

        if appointment_id is None:
            appointment_id = appointment.get("id")
        if appointment_id is None:
            appointment_id = appointment.get("agendamentoId")
        existing = None
        if appointment_id is not None:
            existing = next(
                (item for item in records if item.get("id") == appointment_id),
                None,
            )
            if existing is None and require_existing:
                raise ServiceError("Agendamento não encontrado", 404)
            appointment = {
                **(existing or {}),
                **appointment,
                "id": appointment_id,
            }

        patient_id = as_id(
            appointment.get("pacienteId", appointment.get("paciente_id"))
        )
        doctor_id = as_id(appointment.get("medicoId", appointment.get("medico_id")))
        date = str(appointment.get("data", "")).strip()
        hour = str(appointment.get("hora", appointment.get("horario", ""))).strip()

        if not isinstance(patient_id, int) or not isinstance(doctor_id, int):
            raise ServiceError("Paciente e médico são obrigatórios", 400)
        if not date or not hour:
            raise ServiceError("Data e horário são obrigatórios", 400)

        patient = next(
            (
                item
                for item in self.repository.get_all("pacientes")
                if as_id(item.get("id")) == patient_id
            ),
            None,
        )
        if patient is None:
            raise ServiceError("Paciente não encontrado", 404)

        doctor = next(
            (
                item
                for item in self.repository.get_all("medicos")
                if as_id(item.get("id")) == doctor_id
            ),
            None,
        )
        if doctor is None:
            raise ServiceError("Médico não encontrado", 404)

        appointment.update(
            {
                "pacienteId": patient_id,
                "paciente_id": patient_id,
                "medicoId": doctor_id,
                "medico_id": doctor_id,
                "data": date,
                "hora": hour,
                "pacienteNome": appointment.get("pacienteNome")
                or patient.get("nome"),
                "pacienteTelefone": appointment.get("pacienteTelefone")
                or patient.get("telefone", ""),
                "medicoNome": appointment.get("medicoNome") or doctor.get("nome"),
                "medicoEspecialidade": appointment.get("medicoEspecialidade")
                or doctor.get("especialidade"),
                "status": appointment.get("status") or "agendado",
            }
        )

        inactive_statuses = {"cancelado", "cancelada", "concluido", "concluida"}
        if normalize_text(appointment["status"]) not in inactive_statuses and not (
            self.is_slot_available(
                doctor_id,
                date,
                hour,
                exclude_appointment_id=appointment_id,
            )
        ):
            raise ServiceError("Horário indisponível para este médico", 409)

        if existing is None:
            appointment["id"] = (
                max((item.get("id", 0) for item in records), default=0) + 1
                if appointment_id is None
                else appointment_id
            )
            self.repository.insert("agendamentos", appointment)
        else:
            self.repository.replace("agendamentos", appointment)

        return normalize_appointment(appointment), 201 if appointment_id is None else 200

    def create_legacy_appointment(self, payload):
        appointment, _ = self.save_appointment(payload)
        return appointment

    def get_appointment(self, appointment_id):
        appointment = next(
            (
                item
                for item in self.repository.get_all("agendamentos")
                if item.get("id") == appointment_id
            ),
            None,
        )
        if appointment is None:
            raise ServiceError("Agendamento não encontrado", 404)
        return normalize_appointment(appointment)

    def delete_appointment(self, appointment_id):
        appointment = next(
            (
                item
                for item in self.repository.get_all("agendamentos")
                if item.get("id") == appointment_id
            ),
            None,
        )
        if appointment is None:
            raise ServiceError("Agendamento não encontrado", 404)
        self.repository.delete("agendamentos", appointment_id)
        return {
            "mensagem": "Agendamento excluído",
            "agendamento": normalize_appointment(appointment),
        }

    def is_slot_available(
        self, doctor_id, date, hour, exclude_appointment_id=None
    ):
        if not date or not hour:
            return True
        target = (as_id(doctor_id), str(date), str(hour))
        for appointment in self.repository.get_all("agendamentos"):
            if appointment.get("id") == exclude_appointment_id:
                continue
            if normalize_text(appointment.get("status")) in {
                "cancelado",
                "cancelada",
                "concluido",
                "concluida",
            }:
                continue
            occupied_slot = (
                as_id(appointment.get("medicoId", appointment.get("medico_id"))),
                str(appointment.get("data", "")),
                str(appointment.get("hora", appointment.get("horario", ""))),
            )
            if occupied_slot == target:
                return False
        return True

    def get_availability(self, doctor_id, date, hours):
        return {
            "medicoId": doctor_id,
            "data": date,
            "horarios": [
                {
                    "hora": hour,
                    "disponivel": self.is_slot_available(doctor_id, date, hour),
                }
                for hour in (hours or DEFAULT_SLOTS)
            ],
        }
