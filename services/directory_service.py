from repositories.data_repository import DataRepository
from services.errors import ServiceError
from services.helpers import as_id


class DirectoryService:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    def list_records(self, collection):
        return self.repository.get_all(collection)

    def save_record(self, collection, payload, truthy_status=False):
        records = self.repository.get_all(collection)
        record = dict(payload)
        record_id = record.get("id")
        if record_id is None:
            record["id"] = max((item.get("id", 0) for item in records), default=0) + 1
            record.setdefault("status", "ativo")
            self.repository.insert(collection, record)
        else:
            existing = next(
                (item for item in records if item.get("id") == record_id),
                {},
            )
            record = {**existing, **record}
            self.repository.replace(collection, record)
        if truthy_status:
            status_code = 201 if not record_id else 200
        else:
            status_code = 201 if record_id is None else 200
        return record, status_code

    def get_record(self, collection, record_id, label):
        record = next(
            (
                item
                for item in self.repository.get_all(collection)
                if item.get("id") == record_id
            ),
            None,
        )
        if record is None:
            raise ServiceError(f"{label} não encontrado", 404)
        return record

    def delete_record(
        self, collection, record_id, label, response_key=None, message=None
    ):
        record = next(
            (
                item
                for item in self.repository.get_all(collection)
                if item.get("id") == record_id
            ),
            None,
        )
        if record is None:
            raise ServiceError(f"{label} não encontrado", 404)
        self.repository.delete(collection, record_id)
        if response_key:
            return {"mensagem": message or f"{label} excluído", response_key: record}
        return {"mensagem": message or f"{label} excluído"}

    def list_history(self):
        return self.repository.get_all("historico")

    def create_history(self, payload):
        records = self.repository.get_all("historico")
        record = dict(payload)
        record["id"] = max((item.get("id", 0) for item in records), default=0) + 1
        self.repository.insert("historico", record)
        return record

    def get_settings(self):
        return self.repository.get_document("config")

    def update_settings(self, payload):
        settings = self.repository.get_document("config")
        settings.update(payload)
        self.repository.save_document("config", settings)
        return settings

    def get_doctor_for_availability(self, doctor_id):
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
        return doctor
