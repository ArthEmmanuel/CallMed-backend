import hmac
import re

from werkzeug.security import check_password_hash, generate_password_hash

from repositories.data_repository import DataRepository
from services.authorization import is_admin
from services.errors import ServiceError
from services.helpers import merge_profile, normalize_profile_payload, sanitize_user


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OBJECT_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{24}$")


class UserService:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    def authenticate(self, email, password):
        email = self._validated_email(email)
        if not isinstance(password, str) or not password or len(password) > 256:
            raise ServiceError("Credenciais inválidas", 401)

        user = self.repository.find_by_field("usuarios", "email", email)
        if user is None:
            user = next(
                (
                    item
                    for item in self.repository.get_all("usuarios")
                    if str(item.get("email", "")).casefold() == email
                ),
                None,
            )
        stored_password = user.get("senha") if user else None
        if not isinstance(stored_password, str) or not self._verify_password(
            password, stored_password
        ):
            raise ServiceError("Credenciais inválidas", 401)

        if not self._is_password_hash(stored_password):
            user["senha"] = generate_password_hash(password)
            self.repository.replace("usuarios", user)
        return user

    def login(self, email, password):
        return sanitize_user(self.authenticate(email, password))

    def get_auth_user(self, user_id):
        return self._find_user(self._parse_id(user_id))

    @staticmethod
    def public_user(user):
        return sanitize_user(user)

    def list_users(self, actor):
        self._require_admin(actor)
        return [
            sanitize_user(user)
            for user in self.repository.get_all("usuarios")
        ]

    def get_user(self, user_id, actor):
        user = self._find_user(self._parse_id(user_id))
        self._require_self_or_admin(user, actor)
        return sanitize_user(user)

    def create_user(self, payload, frontend_fields=False, public_registration=False):
        if not isinstance(payload, dict):
            raise ServiceError("Os dados do usuário devem ser um objeto JSON", 400)
        normalized = normalize_profile_payload(payload) if frontend_fields else payload
        name = self._required_text(normalized.get("nome"), "Nome")
        email = self._validated_email(normalized.get("email"))
        password = self._validated_password(normalized.get("senha"))
        if self._find_by_email(email):
            raise ServiceError("E-mail já cadastrado", 409)

        role = str(normalized.get("tipo", "paciente")).strip().casefold()
        if role not in {"paciente", "clinica", "admin"}:
            raise ServiceError("Tipo de usuário inválido", 400)
        if public_registration and role == "admin":
            raise ServiceError("Não é permitido criar administrador pelo cadastro", 403)

        user = {
            "id": self._next_numeric_id("usuarios"),
            "nome": name,
            "email": email,
            "senha": generate_password_hash(password),
            "tipo": role,
        }
        if role == "admin":
            user["tipoClinica"] = "admin"

        self.repository.insert("usuarios", user)
        if role == "paciente":
            try:
                self.repository.insert(
                    "pacientes",
                    {
                        "id": user["id"],
                        "nome": name,
                        "email": email,
                        "telefone": "",
                        "dataNascimento": "",
                        "usuarioId": user["id"],
                        "status": "ativo",
                    },
                )
            except Exception:
                self.repository.delete("usuarios", user["id"])
                raise
        return sanitize_user(user)

    def update_user(self, user_id, payload, actor):
        if not isinstance(payload, dict) or not payload:
            raise ServiceError("Informe os dados que deseja atualizar", 400)
        user = self._find_user(self._parse_id(user_id))
        self._require_self_or_admin(user, actor)
        fields = normalize_profile_payload(payload)
        allowed = {"nome", "email", "senha", "telefone"}
        if is_admin(actor):
            allowed.add("tipo")
            allowed.add("tipoClinica")
        updates = {key: value for key, value in fields.items() if key in allowed}
        if is_admin(actor) and "tipoClinica" in payload:
            updates["tipoClinica"] = payload["tipoClinica"]
        if not updates:
            raise ServiceError("Nenhum campo permitido para atualização", 400)

        updates = self._validate_user_updates(user, updates)
        user.update(updates)
        self.repository.replace("usuarios", user)
        self._sync_patient_profile(user, updates)
        return sanitize_user(user)

    def delete_user(self, user_id, actor):
        user = self._find_user(self._parse_id(user_id))
        self._require_self_or_admin(user, actor)
        self.repository.delete("usuarios", user["id"])
        self.repository.delete_by_field("pacientes", "usuarioId", user["id"])
        self.repository.delete("pacientes", user["id"])
        return {"mensagem": "Usuário excluído"}

    def list_admins(self, actor):
        self._require_admin(actor)
        return [
            sanitize_user(user)
            for user in self.repository.get_all("usuarios")
            if self._is_admin(user)
        ]

    def get_admin(self, admin_id, actor):
        self._require_admin(actor)
        return sanitize_user(self._find_admin(self._parse_id(admin_id)))

    def create_admin(self, payload):
        if not isinstance(payload, dict):
            raise ServiceError("Os dados do administrador devem ser um objeto JSON", 400)
        name = self._required_text(payload.get("nome"), "Nome")
        email = self._validated_email(payload.get("email"))
        password = self._validated_password(payload.get("senha"))
        if self._find_by_email(email):
            raise ServiceError("E-mail já cadastrado", 409)

        admin = {
            "id": self._next_numeric_id("usuarios"),
            "nome": name,
            "email": email,
            "senha": generate_password_hash(password),
            "tipo": "clinica",
            "tipoClinica": "admin",
        }
        self.repository.insert("usuarios", admin)
        return sanitize_user(admin)

    def update_admin(self, admin_id, payload):
        if not isinstance(payload, dict) or not payload:
            raise ServiceError("Informe os dados que deseja atualizar", 400)
        admin = self._find_admin(self._parse_id(admin_id))
        updates = {
            key: payload[key]
            for key in ("nome", "email", "senha")
            if key in payload
        }
        if not updates:
            raise ServiceError("Nenhum campo permitido para atualização", 400)
        admin.update(self._validate_user_updates(admin, updates))
        self.repository.replace("usuarios", admin)
        return sanitize_user(admin)

    def delete_admin(self, admin_id):
        admin = self._find_admin(self._parse_id(admin_id))
        self.repository.delete("usuarios", admin["id"])
        return {"mensagem": "Administrador excluído"}

    def get_profile(self, user_id, actor):
        user = self._find_user(self._parse_id(user_id))
        self._require_self_or_admin(user, actor)
        return merge_profile(user, self._find_patient_profile(user))

    def update_profile(self, user_id, payload, actor):
        if not isinstance(payload, dict) or not payload:
            raise ServiceError("Informe os dados que deseja atualizar", 400)
        user = self._find_user(self._parse_id(user_id))
        self._require_self_or_admin(user, actor)
        normalized = normalize_profile_payload(payload)
        updates = {
            key: normalized[key]
            for key in ("nome", "email", "senha", "telefone")
            if key in normalized
        }
        patient_fields = {
            key: normalized[key]
            for key in ("telefone", "dataNascimento", "data_nascimento")
            if key in normalized
        }
        if not updates and not patient_fields:
            raise ServiceError("Nenhum campo permitido para atualização", 400)
        for key in ("telefone", "dataNascimento", "data_nascimento"):
            if key in patient_fields and not isinstance(patient_fields[key], str):
                raise ServiceError(f"{key} inválido", 400)

        user.update(self._validate_user_updates(user, updates))
        self.repository.replace("usuarios", user)
        self._sync_patient_profile(user, updates)
        patient = self._find_patient_profile(user)
        if patient and patient_fields:
            patient.update(patient_fields)
            if "dataNascimento" in patient_fields:
                patient["data_nascimento"] = patient_fields["dataNascimento"]
            if "data_nascimento" in patient_fields:
                patient["dataNascimento"] = patient_fields["data_nascimento"]
            self.repository.replace("pacientes", patient)
        return merge_profile(user, patient)

    def _validate_user_updates(self, user, updates):
        if "nome" in updates:
            updates["nome"] = self._required_text(updates["nome"], "Nome")
        if "email" in updates:
            updates["email"] = self._validated_email(updates["email"])
            other = self._find_by_email(updates["email"])
            if other and str(other.get("id")) != str(user.get("id")):
                raise ServiceError("E-mail já cadastrado", 409)
        if "telefone" in updates and not isinstance(updates["telefone"], str):
            raise ServiceError("Telefone inválido", 400)
        if "senha" in updates:
            updates["senha"] = generate_password_hash(
                self._validated_password(updates["senha"])
            )
        if "tipo" in updates:
            role = str(updates["tipo"]).strip().casefold()
            if role not in {"paciente", "clinica", "admin"}:
                raise ServiceError("Tipo de usuário inválido", 400)
            updates["tipo"] = role
        return updates

    def _sync_patient_profile(self, user, updates):
        patient = self._find_patient_profile(user)
        if patient is None:
            return
        for key in ("nome", "email", "telefone"):
            if key in updates:
                patient[key] = updates[key]
        self.repository.replace("pacientes", patient)

    def _find_patient_profile(self, user):
        patient = self.repository.find_by_field(
            "pacientes", "usuarioId", user.get("id")
        )
        if patient is None:
            patient = self.repository.get_by_id("pacientes", user.get("id"))
        return patient

    def _find_user(self, user_id):
        user = self.repository.get_by_id("usuarios", user_id)
        if user is None:
            raise ServiceError("Usuário não encontrado", 404)
        return user

    def _find_admin(self, admin_id):
        admin = self.repository.get_by_id("usuarios", admin_id)
        if admin is None or not self._is_admin(admin):
            raise ServiceError("Administrador não encontrado", 404)
        return admin

    def _find_by_email(self, email):
        return self.repository.find_by_field("usuarios", "email", email)

    def _next_numeric_id(self, collection):
        ids = [
            record.get("id")
            for record in self.repository.get_all(collection)
            if isinstance(record.get("id"), int)
            and not isinstance(record.get("id"), bool)
        ]
        return max(ids, default=0) + 1

    @staticmethod
    def _validated_email(value):
        if not isinstance(value, str):
            raise ServiceError("E-mail é obrigatório", 400)
        email = value.strip().casefold()
        if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            raise ServiceError("E-mail inválido", 400)
        return email

    @staticmethod
    def _required_text(value, label):
        if not isinstance(value, str) or not value.strip():
            raise ServiceError(f"{label} é obrigatório", 400)
        return value.strip()

    @staticmethod
    def _validated_password(value):
        if not isinstance(value, str) or not value or len(value) > 256:
            raise ServiceError("Senha inválida", 400)
        return value

    @staticmethod
    def _is_password_hash(value):
        return value.startswith(("scrypt:", "pbkdf2:"))

    @classmethod
    def _verify_password(cls, password, stored_password):
        if cls._is_password_hash(stored_password):
            try:
                return check_password_hash(stored_password, password)
            except ValueError:
                return False
        return hmac.compare_digest(stored_password, password)

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
    def _is_admin(user):
        return is_admin(user)

    @classmethod
    def _require_admin(cls, actor):
        if not is_admin(actor):
            raise ServiceError("Acesso não autorizado", 403)

    @classmethod
    def _require_self_or_admin(cls, target, actor):
        if is_admin(actor):
            return
        if str(target.get("id")) != str(actor.get("id")):
            raise ServiceError("Acesso não autorizado", 403)
