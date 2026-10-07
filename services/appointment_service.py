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

    def save_appointment(self, payload):
        records = self.repository.get_all("agendamentos")
        appointment = dict(payload)
        appointment_id = appointment.get("id")
        if appointment_id is None:
            appointment_id = appointment.get("agendamentoId")

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
            appointment["id"] = (
                max((item.get("id", 0) for item in records), default=0) + 1
            )
            records.append(appointment)
        else:
            self._upsert(records, appointment, appointment_id)

        self.repository.save_all("agendamentos", records)
        return normalize_appointment(appointment), 201 if not appointment_id else 200

    def create_legacy_appointment(self, payload):
        records = self.repository.get_all("agendamentos")
        appointment = dict(payload)
        appointment.setdefault(
            "id",
            max((item.get("id", 0) for item in records), default=0) + 1,
        )
        records.append(appointment)
        self.repository.save_all("agendamentos", records)
        return normalize_appointment(appointment)

    def delete_appointment(self, appointment_id):
        records = self.repository.get_all("agendamentos")
        appointment = next(
            (item for item in records if item.get("id") == appointment_id),
            None,
        )
        if appointment is None:
            raise ServiceError("Agendamento não encontrado", 404)
        records.remove(appointment)
        self.repository.save_all("agendamentos", records)
        return {
            "mensagem": "Agendamento excluído",
            "agendamento": normalize_appointment(appointment),
        }

    def is_slot_available(self, doctor_id, date, hour):
        if not date or not hour:
            return True
        target = (as_id(doctor_id), str(date), str(hour))
        for appointment in self.repository.get_all("agendamentos"):
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

    @staticmethod
    def _upsert(records, record, record_id):
        for index, item in enumerate(records):
            if item.get("id") == record_id:
                records[index] = {**item, **record}
                return
        records.append(record)
