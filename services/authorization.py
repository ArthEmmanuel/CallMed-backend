def is_admin(user):
    return bool(user) and (
        str(user.get("tipoClinica", "")).casefold() == "admin"
        or str(user.get("tipo", "")).casefold() == "admin"
    )


def user_role(user):
    role = str(user.get("tipo", "")).casefold()
    clinic_role = str(user.get("tipoClinica", "")).casefold()
    if role == "paciente":
        return "paciente"
    if role == "medico" or clinic_role in {"medico", "médico"}:
        return "medico"
    return role
