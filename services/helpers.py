def as_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def sanitize_user(user):
    if user is None:
        return None
    response = dict(user)
    response.pop("senha", None)
    return response


def normalize_profile_payload(payload):
    if not isinstance(payload, dict):
        return {}

    normalized = {}
    allowed_keys = {
        "nome",
        "email",
        "senha",
        "telefone",
        "tipo",
        "dataNascimento",
        "data_nascimento",
        "birthDate",
    }
    for key, value in payload.items():
        if key in allowed_keys:
            normalized[key] = value

    aliases = {
        "name": "nome",
        "Email": "email",
        "password": "senha",
        "phone": "telefone",
    }
    for alias, canonical in aliases.items():
        if canonical not in normalized and alias in payload:
            normalized[canonical] = payload[alias]

    if "tipo" not in normalized:
        for alias in ("type", "tipoUsuario", "userType"):
            if alias in payload:
                normalized["tipo"] = payload[alias]
                break

    if "dataNascimento" not in normalized:
        for alias in ("data_nascimento", "birthDate", "birthdate"):
            if alias in payload:
                normalized["dataNascimento"] = payload[alias]
                break

    return normalized


def merge_profile(user, paciente=None):
    base = sanitize_user(user) or {}
    profile = dict(base)

    if paciente:
        profile.update(
            {
                "id": paciente.get("id", user.get("id") if user else None),
                "usuarioId": user.get("id") if user else paciente.get("usuarioId"),
                "telefone": paciente.get("telefone") or profile.get("telefone"),
                "dataNascimento": (
                    paciente.get("dataNascimento")
                    or paciente.get("data_nascimento")
                    or profile.get("dataNascimento")
                ),
                "data_nascimento": (
                    paciente.get("data_nascimento")
                    or paciente.get("dataNascimento")
                    or profile.get("data_nascimento")
                ),
                "status": paciente.get("status") or profile.get("status"),
            }
        )

    if "telefone" not in profile and user and "telefone" in user:
        profile["telefone"] = user.get("telefone")
    return profile


def normalize_appointment(appointment):
    item = dict(appointment)
    aliases = {
        "pacienteId": "paciente_id",
        "medicoId": "medico_id",
        "pacienteNome": "paciente_nome",
        "pacienteTelefone": "paciente_telefone",
        "medicoNome": "medico_nome",
        "medicoEspecialidade": "medico_especialidade",
    }
    for camel_key, snake_key in aliases.items():
        if camel_key not in item and snake_key in item:
            item[camel_key] = item[snake_key]
        if snake_key not in item and camel_key in item:
            item[snake_key] = item[camel_key]
    return item
