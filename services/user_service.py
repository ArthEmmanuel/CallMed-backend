from repositories.data_repository import DataRepository
from services.errors import ServiceError
from services.helpers import merge_profile, normalize_profile_payload, sanitize_user


class UserService:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    def login(self, email, password):
        user = next(
            (
                item
                for item in self.repository.get_all("usuarios")
                if str(item.get("email", "")).lower() == email
                and str(item.get("senha", "")) == password
            ),
            None,
        )
        if user is None:
            raise ServiceError("Credenciais inválidas", 401)
        return sanitize_user(user)

    def list_users(self):
        return [sanitize_user(user) for user in self.repository.get_all("usuarios")]

    def get_user(self, user_id):
        user = next(
            (
                item
                for item in self.repository.get_all("usuarios")
                if item.get("id") == user_id
            ),
            None,
        )
        if user is None:
            raise ServiceError("Usuário não encontrado", 404)
        return sanitize_user(user)

    def create_user(self, payload, frontend_fields=False):
        normalized = normalize_profile_payload(payload) if frontend_fields else payload
        nome = str(normalized.get("nome", "") or "").strip()
        email = str(normalized.get("email", "") or "").strip().lower()
        senha = str(normalized.get("senha", "") or "").strip()
        if not nome or not email or not senha:
            raise ServiceError("Nome, e-mail e senha são obrigatórios", 400)

        users = self.repository.get_all("usuarios")
        if any(str(user.get("email", "")).lower() == email for user in users):
            raise ServiceError("E-mail já cadastrado", 409)

        user_id = max((user.get("id", 0) for user in users), default=0) + 1
        user = {
            "id": user_id,
            "nome": nome,
            "email": email,
            "senha": senha,
            "tipo": normalized.get("tipo", payload.get("tipo", "paciente")),
        }
        self.repository.insert("usuarios", user)

        if user["tipo"] == "paciente":
            self.repository.insert(
                "pacientes",
                {
                    "id": user_id,
                    "nome": nome,
                    "email": email,
                    "telefone": "",
                    "dataNascimento": "",
                    "usuarioId": user_id,
                    "status": "ativo",
                },
            )
        return sanitize_user(user)

    def get_profile(self, user_id):
        user = self._find_user(user_id)
        patient = next(
            (
                item
                for item in self.repository.get_all("pacientes")
                if item.get("usuarioId") == user_id or item.get("id") == user_id
            ),
            None,
        )
        return merge_profile(user, patient)

    def update_profile(self, user_id, payload):
        user = self._find_user(user_id)
        patient = next(
            (
                item
                for item in self.repository.get_all("pacientes")
                if item.get("usuarioId") == user_id or item.get("id") == user_id
            ),
            None,
        )
        normalized = normalize_profile_payload(payload)
        for field in ("nome", "email", "senha", "tipo"):
            if field in normalized:
                user[field] = normalized[field]

        self.repository.replace("usuarios", user)

        if patient:
            for field in ("telefone", "dataNascimento", "data_nascimento"):
                if field in normalized:
                    patient[field] = normalized[field]
                    if field in {"dataNascimento", "data_nascimento"}:
                        patient[
                            "data_nascimento"
                            if field == "dataNascimento"
                            else "dataNascimento"
                        ] = normalized[field]
            self.repository.replace("pacientes", patient)

        return merge_profile(user, patient)

    def _find_user(self, user_id):
        user = next(
            (
                item
                for item in self.repository.get_all("usuarios")
                if item.get("id") == user_id
            ),
            None,
        )
        if user is None:
            raise ServiceError("Usuário não encontrado", 404)
        return user
