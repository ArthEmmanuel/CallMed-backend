import re
from typing import Any

from repositories.data_repository import DataRepository
from services.authorization import is_admin, user_role
from services.errors import ServiceError


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OBJECT_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{24}$")


class DirectoryService:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    def list_records(self, collection: str, actor: dict[str, Any]):
        if collection == "pacientes" and not is_admin(actor):
            raise ServiceError("Acesso não autorizado", 403)
        return self.repository.get_all(collection)

    def save_record(
        self,
        collection: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        truthy_status: bool = False,
    ):
        if not isinstance(payload, dict):
            raise ServiceError("Os dados devem ser um objeto JSON", 400)
        records = self.repository.get_all(collection)
        supplied_id = payload.get("id")
        record_id = self._parse_id(supplied_id) if supplied_id is not None else None

        if record_id is None:
            record = dict(payload)
            record["id"] = self._next_numeric_id(records)
            record.setdefault("status", "ativo")
            self._authorize_create(collection, record, actor)
            self._validate_profile(collection, record, creating=True)
            self.repository.insert(collection, record)
        else:
            record = self.repository.get_by_id(collection, record_id)
            if record is None:
                raise ServiceError(f"{self._label(collection)} não encontrado", 404)
            self._authorize_record(collection, record, actor, read=False)
            self._apply_updates(collection, record, payload, actor)
            self.repository.replace(collection, record)

        status_code = (
            201 if supplied_id is None else 200
        ) if not truthy_status else (201 if not supplied_id else 200)
        return record, status_code

    def get_record(
        self,
        collection: str,
        record_id: int | str,
        label: str,
        actor: dict[str, Any],
        read: bool = False,
    ):
        parsed_id = self._parse_id(record_id)
        record = self.repository.get_by_id(collection, parsed_id)
        if record is None:
            raise ServiceError(f"{label} não encontrado", 404)
        self._authorize_record(collection, record, actor, read=read)
        return record

    def update_record(
        self,
        collection: str,
        record_id: int | str,
        payload: dict[str, Any],
        label: str,
        actor: dict[str, Any],
    ):
        if not isinstance(payload, dict) or not payload:
            raise ServiceError("Informe os dados que deseja atualizar", 400)
        record = self.get_record(
            collection, record_id, label, actor, read=False
        )
        self._apply_updates(collection, record, payload, actor)
        self.repository.replace(collection, record)
        return record

    def delete_record(
        self,
        collection: str,
        record_id: int | str,
        label: str,
        response_key: str | None = None,
        message: str | None = None,
        actor: dict[str, Any] | None = None,
    ):
        record = self.get_record(
            collection,
            record_id,
            label,
            actor or {},
            read=False,
        )
        self.repository.delete(collection, record["id"])
        if response_key:
            return {"mensagem": message or f"{label} excluído", response_key: record}
        return {"mensagem": message or f"{label} excluído"}

    def list_history(self, actor):
        self._require_admin(actor)
        return self.repository.get_all("historico")

    def create_history(self, payload, actor):
        self._require_admin(actor)
        if not isinstance(payload, dict):
            raise ServiceError("Os dados do histórico devem ser um objeto JSON", 400)
        records = self.repository.get_all("historico")
        record = dict(payload)
        record["id"] = self._next_numeric_id(records)
        self.repository.insert("historico", record)
        return record

    def get_history(self, history_id, actor):
        self._require_admin(actor)
        return self.get_record(
            "historico", history_id, "Registro de histórico", actor
        )

    def update_history(self, history_id, payload, actor):
        self._require_admin(actor)
        if not isinstance(payload, dict) or not payload:
            raise ServiceError("Informe os dados que deseja atualizar", 400)
        record = self.get_history(history_id, actor)
        protected_fields = {"id", "_id"}
        record.update(
            {
                key: value
                for key, value in payload.items()
                if key not in protected_fields
            }
        )
        self.repository.replace("historico", record)
        return record

    def delete_history(self, history_id, actor):
        self._require_admin(actor)
        return self.delete_record(
            "historico",
            history_id,
            "Registro de histórico",
            actor=actor,
        )

    def get_settings(self, actor):
        self._require_admin(actor)
        return self.repository.get_document("config")

    def update_settings(self, payload, actor):
        self._require_admin(actor)
        if not isinstance(payload, dict) or not payload:
            raise ServiceError("Informe as configurações que deseja atualizar", 400)
        settings = self.repository.get_document("config")
        settings.update(payload)
        self.repository.save_document("config", settings)
        return settings

    def replace_settings(self, payload, actor):
        self._require_admin(actor)
        if not isinstance(payload, dict) or not payload:
            raise ServiceError("Informe as configurações que deseja salvar", 400)
        current = self.repository.get_document("config")
        settings = dict(payload)
        if "id" in current:
            settings["id"] = current["id"]
        self.repository.replace_document("config", settings)
        return settings

    def delete_settings(self, actor):
        self._require_admin(actor)
        if not self.repository.delete_document("config"):
            raise ServiceError("Configuração não encontrada", 404)
        return {"mensagem": "Configuração excluída"}

    def list_user_settings(self, actor):
        records = self.repository.get_all("configuracoes_usuario")
        if is_admin(actor):
            return records
        return [
            record
            for record in records
            if self._setting_owner_id(record) == str(actor.get("id"))
        ]

    def create_user_setting(self, payload, actor):
        if not isinstance(payload, dict) or not payload:
            raise ServiceError(
                "Os dados da configuração devem ser um objeto JSON", 400
            )

        record = {
            key: value
            for key, value in payload.items()
            if key not in {"id", "_id", "usuarioId", "usuario_id", "userId"}
        }
        owner_id = actor.get("id")
        if is_admin(actor):
            requested_owner = (
                payload.get("usuarioId")
                or payload.get("usuario_id")
                or payload.get("userId")
            )
            if requested_owner is not None:
                owner = self.repository.get_by_id("usuarios", requested_owner)
                if owner is None:
                    raise ServiceError("Usuário vinculado não encontrado", 404)
                owner_id = owner["id"]
        record["id"] = self._next_numeric_id(
            self.repository.get_all("configuracoes_usuario")
        )
        record["usuarioId"] = owner_id
        self.repository.insert("configuracoes_usuario", record)
        return record

    def get_user_setting(self, setting_id, actor):
        record = self.repository.get_by_id(
            "configuracoes_usuario", self._parse_id(setting_id)
        )
        if record is None:
            raise ServiceError("Configuração do usuário não encontrada", 404)
        self._authorize_user_setting(record, actor)
        return record

    def update_user_setting(self, setting_id, payload, actor):
        if not isinstance(payload, dict) or not payload:
            raise ServiceError("Informe os dados que deseja atualizar", 400)
        record = self.get_user_setting(setting_id, actor)
        record.update(
            {
                key: value
                for key, value in payload.items()
                if key not in {"id", "_id", "usuarioId", "usuario_id", "userId"}
            }
        )
        self.repository.replace("configuracoes_usuario", record)
        return record

    def delete_user_setting(self, setting_id, actor):
        record = self.get_user_setting(setting_id, actor)
        self.repository.delete("configuracoes_usuario", record["id"])
        return {"mensagem": "Configuração do usuário excluída"}

    def get_doctor_for_availability(self, doctor_id, actor):
        doctor = self.get_record(
            "medicos",
            doctor_id,
            "Médico",
            actor,
            read=True,
        )
        return doctor

    def _authorize_create(self, collection, record, actor):
        if collection not in {"pacientes", "medicos"}:
            if not is_admin(actor):
                raise ServiceError("Acesso não autorizado", 403)
            return
        if is_admin(actor):
            user_id = record.get("usuarioId")
            if user_id is not None:
                user = self.repository.get_by_id("usuarios", user_id)
                if user is None:
                    raise ServiceError("Usuário vinculado não encontrado", 404)
                record["usuarioId"] = user["id"]
                if self.repository.find_by_field(
                    collection, "usuarioId", user["id"]
                ):
                    raise ServiceError("Este usuário já possui um perfil", 409)
            return

        required_role = "paciente" if collection == "pacientes" else "medico"
        if user_role(actor) != required_role:
            raise ServiceError("Acesso não autorizado", 403)
        if self.repository.find_by_field(collection, "usuarioId", actor["id"]):
            raise ServiceError("Este usuário já possui um perfil", 409)
        record["usuarioId"] = actor["id"]
        record["nome"] = record.get("nome") or actor.get("nome")
        record["email"] = record.get("email") or actor.get("email")

    def _authorize_record(self, collection, record, actor, read):
        if is_admin(actor):
            return
        if collection == "medicos" and read:
            return
        if collection == "especialidades" and read:
            return
        if collection not in {"pacientes", "medicos"}:
            raise ServiceError("Acesso não autorizado", 403)

        required_role = "paciente" if collection == "pacientes" else "medico"
        related_id = record.get("usuarioId", record.get("id"))
        owns_record = str(related_id) == str(actor.get("id"))
        if not owns_record and record.get("email"):
            owns_record = (
                str(record["email"]).casefold()
                == str(actor.get("email", "")).casefold()
            )
        if not owns_record or user_role(actor) != required_role:
            raise ServiceError("Acesso não autorizado", 403)

    def _apply_updates(self, collection, record, payload, actor):
        protected_fields = {"id", "_id", "usuarioId", "senha", "tipo", "tipoClinica"}
        if not is_admin(actor) and protected_fields.intersection(payload):
            raise ServiceError("Não é permitido alterar campos protegidos", 403)
        if is_admin(actor) and payload.get("usuarioId") is not None:
            related_user = self.repository.get_by_id(
                "usuarios", payload["usuarioId"]
            )
            if related_user is None:
                raise ServiceError("Usuário vinculado não encontrado", 404)
            record["usuarioId"] = related_user["id"]
        updates = {
            key: value
            for key, value in payload.items()
            if key not in protected_fields
        }
        record.update(updates)
        self._validate_profile(collection, record, creating=False)

    def _validate_profile(self, collection, record, creating):
        if collection == "pacientes":
            if creating and not str(record.get("nome", "")).strip():
                raise ServiceError("Nome do paciente é obrigatório", 400)
        elif collection == "medicos":
            if creating and not str(record.get("nome", "")).strip():
                raise ServiceError("Nome do médico é obrigatório", 400)
            if creating and not str(record.get("especialidade", "")).strip():
                raise ServiceError("Especialidade do médico é obrigatória", 400)
            if "perfil" in record and not isinstance(record["perfil"], dict):
                raise ServiceError("Perfil do médico deve ser um objeto", 400)

        email = record.get("email")
        if email is not None:
            if not isinstance(email, str) or not EMAIL_PATTERN.fullmatch(email.strip()):
                raise ServiceError("E-mail inválido", 400)
            record["email"] = email.strip().casefold()
            existing = self.repository.find_by_field(
                collection, "email", record["email"]
            )
            if existing and str(existing.get("id")) != str(record.get("id")):
                raise ServiceError("E-mail já cadastrado", 409)

    def _next_numeric_id(self, records):
        ids = [
            record.get("id")
            for record in records
            if isinstance(record.get("id"), int)
            and not isinstance(record.get("id"), bool)
        ]
        return max(ids, default=0) + 1

    @staticmethod
    def _parse_id(value):
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if not isinstance(value, str) or not value.strip():
            raise ServiceError("ID inválido", 400)
        value = value.strip()
        if OBJECT_ID_PATTERN.fullmatch(value):
            return value
        if value.isdecimal():
            return int(value)
        raise ServiceError("ID inválido", 400)

    @staticmethod
    def _label(collection):
        return {
            "pacientes": "Paciente",
            "medicos": "Médico",
        }.get(collection, "Registro")

    @staticmethod
    def _require_admin(actor):
        if not is_admin(actor):
            raise ServiceError("Acesso não autorizado", 403)

    @staticmethod
    def _setting_owner_id(record):
        owner_id = record.get(
            "usuarioId",
            record.get("usuario_id", record.get("userId")),
        )
        return str(owner_id) if owner_id is not None else None

    @classmethod
    def _authorize_user_setting(cls, record, actor):
        if is_admin(actor):
            return
        if cls._setting_owner_id(record) != str(actor.get("id")):
            raise ServiceError("Acesso não autorizado", 403)
