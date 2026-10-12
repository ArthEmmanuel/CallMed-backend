from functools import wraps

from flask import current_app, g, jsonify, request

from services.authorization import is_admin


def token_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if scheme.casefold() != "bearer" or not separator or not token.strip():
            return jsonify({"erro": "Token de autenticação obrigatório"}), 401

        user = current_app.extensions["auth_service"].user_from_token(token.strip())
        if user is None:
            return jsonify({"erro": "Token inválido ou expirado"}), 401
        g.authenticated_user = user
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @token_required
    def wrapped(*args, **kwargs):
        if not is_admin(g.authenticated_user):
            return jsonify({"erro": "Acesso não autorizado"}), 403
        return view(*args, **kwargs)

    return wrapped
