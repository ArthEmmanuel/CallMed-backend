from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from services.errors import ServiceError
from services.user_service import UserService


class AuthService:
    def __init__(
        self,
        users: UserService,
        secret_key: str,
        token_max_age_seconds: int,
    ):
        if not secret_key:
            raise RuntimeError(
                "SECRET_KEY não definida. Configure-a no .env do backend."
            )
        self.users = users
        self.token_max_age_seconds = token_max_age_seconds
        self.serializer = URLSafeTimedSerializer(
            secret_key,
            salt="callmed-auth-token",
        )

    def login(self, email, password):
        user = self.users.authenticate(email, password)
        return {
            "mensagem": "Login realizado com sucesso",
            "token": self.serializer.dumps({"sub": str(user["id"])}),
            "tipo_token": "Bearer",
            "expires_in": self.token_max_age_seconds,
            "usuario": self.users.public_user(user),
        }

    def user_from_token(self, token):
        try:
            payload = self.serializer.loads(
                token,
                max_age=self.token_max_age_seconds,
            )
        except (BadSignature, SignatureExpired):
            return None

        user_id = payload.get("sub") if isinstance(payload, dict) else None
        if not user_id:
            return None
        try:
            return self.users.get_auth_user(user_id)
        except ServiceError as error:
            if error.status_code == 404:
                return None
            raise
