import json
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "db.json"

DEFAULT_DATA = {
    "usuarios": [
        {
            "id": 1,
            "nome": "Admin",
            "email": "admin@AgendaMed.com",
            "senha": "123456",
            "tipo": "clinica",
            "tipoClinica": "admin",
        },
        {
            "id": 2,
            "nome": "Dr. Altemar",
            "email": "altemar@clinica.com",
            "senha": "123456",
            "tipo": "clinica",
            "tipoClinica": "medico",
        },
        {
            "id": 3,
            "nome": "João da Silva",
            "email": "joao@AgendaMed.com",
            "senha": "123456",
            "tipo": "paciente",
        },
    ],
    "medicos": [
        {
            "id": 2,
            "nome": "Dr. Altemar",
            "especialidade": "Clínica Geral",
            "crm": "123456-SP",
            "telefone": "(11) 99999-9999",
            "email": "altemar@clinica.com",
            "status": "ativo",
        },
        {
            "id": 4,
            "nome": "Dra. Ana Souza",
            "especialidade": "Cardiologia",
            "crm": "654321-SP",
            "telefone": "(11) 98888-7777",
            "email": "ana@AgendaMed.com",
            "status": "ativo",
        },
    ],
    "pacientes": [
        {
            "id": 3,
            "nome": "João da Silva",
            "data_nascimento": "1990-04-12",
            "telefone": "(11) 98888-8888",
            "email": "joao@AgendaMed.com",
            "status": "ativo",
        }
    ],
    "agendamentos": [
        {
            "id": 1,
            "paciente_id": 3,
            "medico_id": 2,
            "data": "2025-10-15",
            "hora": "14:00",
            "status": "Confirmado",
        }
    ],
    "historico": [
        {
            "id": 1,
            "paciente_id": 3,
            "medico_id": 2,
            "data": "2025-09-20",
            "descricao": "Consulta de rotina.",
        }
    ],
    "clinicas": [],
    "config": {"tema": "light", "notificacoes": True},
}


def merge_default_records(data):
    for key, default_value in DEFAULT_DATA.items():
        if not isinstance(default_value, list):
            data.setdefault(key, default_value)
            continue

        existing = data.get(key, [])
        if not isinstance(existing, list):
            data[key] = list(default_value)
            continue

        existing_by_id = {item.get("id"): item for item in existing if isinstance(item, dict) and item.get("id") is not None}
        for item in default_value:
            item_id = item.get("id")
            if item_id is not None and item_id not in existing_by_id:
                existing.append(item)
                existing_by_id[item_id] = item
        data[key] = existing

    return data


def load_data():
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
                if not isinstance(data, dict):
                    data = {}
                merged = {**DEFAULT_DATA, **data}
                merged = merge_default_records(merged)
                return merged
        except (json.JSONDecodeError, OSError):
            pass

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(DEFAULT_DATA, file, indent=2, ensure_ascii=False)
    return DEFAULT_DATA.copy()


def save_data():
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(DATA, file, indent=2, ensure_ascii=False)


DATA = load_data()

MATCH_SPECIALTY_RULES = {
    "cardiologia": ["cardiologia", "coracao", "pressao", "dor no peito", "palpitacao", "falta de ar", "arritmia", "taquicardia"],
    "dermatologia": ["dermatologia", "pele", "mancha", "coceira", "erupcao", "acne"],
    "pediatria": ["pediatria", "crianca", "bebe", "infantil", "febre infantil"],
    "ortopedia": ["ortopedia", "osso", "fratura", "joelho", "coluna", "ombro", "entorse"],
    "oftalmologia": ["oftalmologia", "olho", "visao", "miopia", "vista", "conjuntivite"],
    "psiquiatria": ["psiquiatria", "ansiedade", "depressao", "estresse", "insonia"],
    "ginecologia": ["ginecologia", "menstruacao", "gravidez", "gestacao"],
    "otorrinolaringologia": ["otorrino", "garganta", "nariz", "ouvido", "sinusite", "otite"],
    "neurologia": ["neurologia", "dor de cabeca", "enxaqueca", "tontura", "formigamento"],
    "endocrinologia": ["endocrinologia", "diabetes", "hormonal", "tireoide"],
    "urologia": ["urologia", "urina", "urinario", "rim", "prostata", "calculo renal"],
    "alergologia": ["alergologia", "alergia", "asma", "rinite alergica", "dermatite"],
    "nutrologia": ["nutrologia", "alimentacao", "nutricao", "peso", "obesidade", "dieta"],
    "geriatria": ["geriatria", "idoso", "envelhecimento", "quedas", "memoria"],
    "clinica geral": ["febre", "gripe", "resfriado", "dor", "mal estar", "cansaco", "rotina", "checkup"],
}


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def as_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def is_slot_available(medico_id, data, hora):
    if not data or not hora:
        return True

    target = (as_id(medico_id), str(data), str(hora))
    for appointment in DATA.get("agendamentos", []):
        status = normalize_text(appointment.get("status"))
        if status in {"cancelado", "cancelada", "concluido", "concluida"}:
            continue
        appointment_slot = (
            as_id(appointment.get("medicoId", appointment.get("medico_id"))),
            str(appointment.get("data", "")),
            str(appointment.get("hora", appointment.get("horario", ""))),
        )
        if appointment_slot == target:
            return False
    return True


def get_specialty_matches(necessidade, sintomas=None):
    search_terms = []
    if necessidade:
        search_terms.append(normalize_text(necessidade))
    if sintomas:
        if isinstance(sintomas, str):
            search_terms.append(normalize_text(sintomas))
        else:
            search_terms.extend(normalize_text(s) for s in sintomas)

    all_terms = " ".join(search_terms)
    matches = []
    for especialidade, keywords in MATCH_SPECIALTY_RULES.items():
        score = 0
        for keyword in keywords:
            if keyword in all_terms:
                score += 30 if keyword == normalize_text(necessidade) else 20
        if score > 0:
            matches.append((especialidade, score))
    if not matches:
        matches.append(("clinica geral", 10))
    return sorted(matches, key=lambda item: item[1], reverse=True)


def build_matchmaking_response(paciente_id, necessidade, sintomas=None, data=None, hora=None):
    pacientes = DATA.get("pacientes", [])
    paciente_id = as_id(paciente_id)
    paciente = next((p for p in pacientes if as_id(p.get("id")) == paciente_id), None)
    if paciente is None:
        raise ValueError("Paciente não encontrado")

    matched_specialties = get_specialty_matches(necessidade, sintomas)
    top_specialties = [especialidade for especialidade, _ in matched_specialties[:3]]

    doctors = []
    for medico in DATA.get("medicos", []):
        especialidade = normalize_text(medico.get("especialidade", ""))
        score = 0
        specialty_hits = []

        for especialidade_alvo, specialty_score in matched_specialties:
            alvo = normalize_text(especialidade_alvo)
            if alvo in especialidade or especialidade in alvo:
                specialty_hits.append((especialidade_alvo, specialty_score))
                score += 110 + specialty_score
            elif especialidade == "clinica geral" and alvo == "clinica geral":
                score += 35 + specialty_score

        if any(term in normalize_text(necessidade) for term in ["dor", "febre", "gripe", "cansaco", "mal estar"]) and "clinica geral" in especialidade:
            score += 10

        if data and hora:
            disponivel = is_slot_available(medico.get("id"), data, hora)
            if disponivel:
                score += 40
            else:
                score -= 150
        else:
            disponivel = True

        if "status" in medico and str(medico.get("status", "")).lower() == "ativo":
            score += 5

        if score > 0 and disponivel:
            doctors.append({
                "id": medico.get("id"),
                "nome": medico.get("nome"),
                "especialidade": medico.get("especialidade"),
                "crm": medico.get("crm"),
                "telefone": medico.get("telefone"),
                "score": score,
                "disponibilidade": {"data": data, "hora": hora},
                "disponivel": disponivel,
                "prioridade": "especialidade_e_disponibilidade" if data and hora else "especialidade",
                "specialty_hits": specialty_hits,
            })

    doctors = sorted(doctors, key=lambda item: item["score"], reverse=True)
    recommendations = doctors[:5]

    return {
        "paciente": {"id": paciente.get("id"), "nome": paciente.get("nome")},
        "necessidade": necessidade,
        "triagem": {
            "sintomas": sintomas if isinstance(sintomas, list) else [sintomas] if sintomas else [],
            "especialidades_sugeridas": top_specialties,
            "mensagem": "Triagem automatizada concluída. Foram identificadas especialidades mais compatíveis com a necessidade do paciente.",
        },
        "recomendacoes": recommendations,
    }


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
    for key, value in payload.items():
        if key in {"nome", "email", "senha", "telefone", "tipo", "dataNascimento", "data_nascimento", "birthDate"}:
            normalized[key] = value

    if "nome" not in normalized and "name" in payload:
        normalized["nome"] = payload.get("name")
    if "email" not in normalized and "Email" in payload:
        normalized["email"] = payload.get("Email")
    if "senha" not in normalized and "password" in payload:
        normalized["senha"] = payload.get("password")
    if "telefone" not in normalized and "phone" in payload:
        normalized["telefone"] = payload.get("phone")
    if "tipo" not in normalized:
        for alt_key in ("type", "tipoUsuario", "userType"):
            if alt_key in payload:
                normalized["tipo"] = payload.get(alt_key)
                break
    if "dataNascimento" not in normalized:
        for alt_key in ("data_nascimento", "birthDate", "birthdate"):
            if alt_key in payload:
                normalized["dataNascimento"] = payload.get(alt_key)
                break

    return normalized


def merge_profile(user, paciente=None):
    base = sanitize_user(user) or {}
    profile = dict(base)

    if paciente:
        profile.update({
            "id": paciente.get("id", user.get("id") if user else None),
            "usuarioId": user.get("id") if user else paciente.get("usuarioId"),
            "telefone": paciente.get("telefone") or profile.get("telefone"),
            "dataNascimento": paciente.get("dataNascimento") or paciente.get("data_nascimento") or profile.get("dataNascimento"),
            "data_nascimento": paciente.get("data_nascimento") or paciente.get("dataNascimento") or profile.get("data_nascimento"),
            "status": paciente.get("status") or profile.get("status"),
        })

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


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "AgendaMed API funcionando"})


@app.route("/api/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    senha = str(payload.get("senha", "")).strip()

    if not email or not senha:
        return jsonify({"erro": "E-mail e senha são obrigatórios"}), 400

    usuario = next((u for u in DATA["usuarios"] if str(u.get("email", "")).lower() == email and str(u.get("senha", "")) == senha), None)
    if not usuario:
        return jsonify({"erro": "Credenciais inválidas"}), 401

    retorno = dict(usuario)
    retorno.pop("senha", None)
    return jsonify({"mensagem": "Login realizado com sucesso", "usuario": retorno})


@app.route("/api/usuarios", methods=["GET", "POST"])
def usuarios():
    if request.method == "GET":
        itens = []
        for usuario in DATA["usuarios"]:
            item = dict(usuario)
            item.pop("senha", None)
            itens.append(item)
        return jsonify(itens)

    payload = request.get_json(silent=True) or {}
    nome = str(payload.get("nome", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    senha = str(payload.get("senha", "")).strip()

    if not nome or not email or not senha:
        return jsonify({"erro": "Nome, e-mail e senha são obrigatórios"}), 400

    if any(str(u.get("email", "")).lower() == email for u in DATA["usuarios"]):
        return jsonify({"erro": "E-mail já cadastrado"}), 409

    novo = {
        "id": max((u.get("id", 0) for u in DATA["usuarios"]), default=0) + 1,
        "nome": nome,
        "email": email,
        "senha": senha,
        "tipo": payload.get("tipo", "paciente"),
    }
    DATA["usuarios"].append(novo)
    if novo["tipo"] == "paciente":
        DATA.setdefault("pacientes", []).append({
            "id": novo["id"],
            "nome": nome,
            "email": email,
            "telefone": "",
            "dataNascimento": "",
            "usuarioId": novo["id"],
            "status": "ativo",
        })
    save_data()
    resposta = dict(novo)
    resposta.pop("senha", None)
    return jsonify({"mensagem": "Usuário criado", "usuario": resposta}), 201


@app.route("/api/medicos", methods=["GET", "POST"])
def medicos():
    if request.method == "GET":
        return jsonify(DATA["medicos"])

    payload = request.get_json(silent=True) or {}
    medico = dict(payload)
    medico_id = medico.get("id")

    if medico_id is None:
        medico["id"] = max((m.get("id", 0) for m in DATA["medicos"]), default=0) + 1
        medico.setdefault("status", "ativo")
        DATA["medicos"].append(medico)
    else:
        for index, item in enumerate(DATA["medicos"]):
            if item.get("id") == medico_id:
                DATA["medicos"][index] = {**item, **medico}
                break
        else:
            DATA["medicos"].append(medico)

    save_data()
    return jsonify(medico), 201 if not medico_id else 200


@app.route("/api/pacientes", methods=["GET", "POST"])
def pacientes():
    if request.method == "GET":
        return jsonify(DATA["pacientes"])

    payload = request.get_json(silent=True) or {}
    paciente = dict(payload)
    paciente_id = paciente.get("id")

    if paciente_id is None:
        paciente["id"] = max((p.get("id", 0) for p in DATA["pacientes"]), default=0) + 1
        paciente.setdefault("status", "ativo")
        DATA["pacientes"].append(paciente)
    else:
        for index, item in enumerate(DATA["pacientes"]):
            if item.get("id") == paciente_id:
                DATA["pacientes"][index] = {**item, **paciente}
                break
        else:
            DATA["pacientes"].append(paciente)

    save_data()
    return jsonify(paciente), 201 if not paciente_id else 200


@app.route("/api/agendamentos", methods=["GET", "POST"])
def agendamentos():
    if request.method == "GET":
        return jsonify([normalize_appointment(item) for item in DATA["agendamentos"]])

    payload = request.get_json(silent=True) or {}
    agendamento = dict(payload)
    agendamento_id = agendamento.get("id")

    if agendamento_id is None:
        agendamento_id = agendamento.get("agendamentoId")

    if "pacienteId" in agendamento and "paciente_id" not in agendamento:
        agendamento["paciente_id"] = agendamento.get("pacienteId")
    if "medicoId" in agendamento and "medico_id" not in agendamento:
        agendamento["medico_id"] = agendamento.get("medicoId")
    if "pacienteNome" in agendamento and "paciente_nome" not in agendamento:
        agendamento["paciente_nome"] = agendamento.get("pacienteNome")
    if "medicoNome" in agendamento and "medico_nome" not in agendamento:
        agendamento["medico_nome"] = agendamento.get("medicoNome")
    if "medicoEspecialidade" in agendamento and "medico_especialidade" not in agendamento:
        agendamento["medico_especialidade"] = agendamento.get("medicoEspecialidade")

    if agendamento_id is None:
        agendamento["id"] = max((a.get("id", 0) for a in DATA["agendamentos"]), default=0) + 1
        DATA["agendamentos"].append(agendamento)
    else:
        for index, item in enumerate(DATA["agendamentos"]):
            if item.get("id") == agendamento_id:
                DATA["agendamentos"][index] = {**item, **agendamento}
                break
        else:
            DATA["agendamentos"].append(agendamento)

    save_data()
    return jsonify(normalize_appointment(agendamento)), 201 if not agendamento_id else 200


@app.route("/api/cadastro", methods=["POST"])
def cadastro():
    payload = request.get_json(silent=True) or {}
    normalized = normalize_profile_payload(payload)
    nome = str(normalized.get("nome", "") or "").strip()
    email = str(normalized.get("email", "") or "").strip().lower()
    senha = str(normalized.get("senha", "") or "").strip()

    if not nome or not email or not senha:
        return jsonify({"erro": "Nome, e-mail e senha são obrigatórios"}), 400

    if any(str(u.get("email", "")).lower() == email for u in DATA["usuarios"]):
        return jsonify({"erro": "E-mail já cadastrado"}), 409

    usuario = {
        "id": max((u.get("id", 0) for u in DATA["usuarios"]), default=0) + 1,
        "nome": nome,
        "email": email,
        "senha": senha,
        "tipo": normalized.get("tipo", payload.get("tipo", "paciente")),
    }

    DATA["usuarios"].append(usuario)
    if usuario["tipo"] == "paciente":
        DATA.setdefault("pacientes", []).append({
            "id": usuario["id"],
            "nome": nome,
            "email": email,
            "telefone": "",
            "dataNascimento": "",
            "usuarioId": usuario["id"],
            "status": "ativo",
        })
    save_data()
    return jsonify({"mensagem": "Usuário criado", "usuario": sanitize_user(usuario)}), 201


@app.route("/api/perfil/<int:usuario_id>", methods=["GET", "PUT"])
def perfil(usuario_id):
    usuario = next((u for u in DATA.get("usuarios", []) if u.get("id") == usuario_id), None)
    if usuario is None:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    paciente = next((p for p in DATA.get("pacientes", []) if p.get("usuarioId") == usuario_id or p.get("id") == usuario_id), None)

    if request.method == "GET":
        return jsonify(merge_profile(usuario, paciente)), 200

    payload = request.get_json(silent=True) or {}
    normalized = normalize_profile_payload(payload)

    if "nome" in normalized:
        usuario["nome"] = normalized["nome"]
    if "email" in normalized:
        usuario["email"] = normalized["email"]
    if "senha" in normalized:
        usuario["senha"] = normalized["senha"]
    if "tipo" in normalized:
        usuario["tipo"] = normalized["tipo"]

    if paciente:
        if "telefone" in normalized:
            paciente["telefone"] = normalized["telefone"]
        if "dataNascimento" in normalized:
            paciente["dataNascimento"] = normalized["dataNascimento"]
            paciente["data_nascimento"] = normalized["dataNascimento"]
        if "data_nascimento" in normalized:
            paciente["data_nascimento"] = normalized["data_nascimento"]
            paciente["dataNascimento"] = normalized["data_nascimento"]

    save_data()
    return jsonify(merge_profile(usuario, paciente)), 200


@app.route("/api/clinicas", methods=["GET", "POST"])
def clinicas():
    if request.method == "GET":
        return jsonify(DATA["clinicas"])

    payload = request.get_json(silent=True) or {}
    clinica = dict(payload)
    clinica_id = clinica.get("id")
    if clinica_id is None:
        clinica["id"] = max((item.get("id", 0) for item in DATA["clinicas"]), default=0) + 1
        clinica.setdefault("status", "ativo")
        DATA["clinicas"].append(clinica)
    else:
        for index, item in enumerate(DATA["clinicas"]):
            if item.get("id") == clinica_id:
                DATA["clinicas"][index] = {**item, **clinica}
                break
        else:
            DATA["clinicas"].append(clinica)
    save_data()
    return jsonify(clinica), 201 if clinica_id is None else 200


@app.route("/api/clinicas/<int:clinica_id>", methods=["DELETE"])
def excluir_clinica(clinica_id):
    clinica = next((item for item in DATA["clinicas"] if item.get("id") == clinica_id), None)
    if clinica is None:
        return jsonify({"erro": "Clínica não encontrada"}), 404
    DATA["clinicas"].remove(clinica)
    save_data()
    return jsonify({"mensagem": "Clínica excluída", "clinica": clinica})


@app.route("/api/historico", methods=["GET", "POST"])
def historico():
    if request.method == "GET":
        return jsonify(DATA.get("historico", []))

    payload = request.get_json(silent=True) or {}
    item = dict(payload)
    item["id"] = max((h.get("id", 0) for h in DATA.get("historico", [])), default=0) + 1
    DATA.setdefault("historico", []).append(item)
    save_data()
    return jsonify(item), 201


@app.route("/api/config", methods=["GET", "POST"])
def config():
    if request.method == "GET":
        return jsonify(DATA["config"])

    payload = request.get_json(silent=True) or {}
    DATA["config"].update(payload)
    save_data()
    return jsonify(DATA["config"])


@app.route("/api/matchmaking", methods=["POST"])
def matchmaking():
    payload = request.get_json(silent=True) or {}
    paciente_id = payload.get("paciente_id", payload.get("pacienteId"))
    necessidade = str(payload.get("necessidade", "")).strip()
    sintomas = payload.get("sintomas", payload.get("sintoma", []))
    data = payload.get("data")
    hora = payload.get("hora")

    if not paciente_id:
        return jsonify({"erro": "paciente_id é obrigatório"}), 400
    if not necessidade:
        return jsonify({"erro": "necessidade é obrigatória"}), 400

    try:
        response = build_matchmaking_response(paciente_id, necessidade, sintomas, data, hora)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 404

    return jsonify(response), 200


@app.route("/api/triagem", methods=["POST"])
def triagem():
    payload = request.get_json(silent=True) or {}
    paciente_id = payload.get("paciente_id", payload.get("pacienteId"))
    necessidade = str(payload.get("necessidade", "")).strip()
    sintomas = payload.get("sintomas", [])

    if not paciente_id:
        return jsonify({"erro": "paciente_id é obrigatório"}), 400
    if not necessidade:
        return jsonify({"erro": "necessidade é obrigatória"}), 400

    try:
        response = build_matchmaking_response(paciente_id, necessidade, sintomas)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 404
    return jsonify(response), 200


@app.route("/api/medicos/<int:medico_id>/disponibilidade", methods=["GET"])
def disponibilidade_medico(medico_id):
    medico = next((item for item in DATA.get("medicos", []) if as_id(item.get("id")) == medico_id), None)
    if medico is None:
        return jsonify({"erro": "Médico não encontrado"}), 404

    data = request.args.get("data")
    horarios = request.args.getlist("hora") or ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"]
    return jsonify({
        "medicoId": medico_id,
        "data": data,
        "horarios": [
            {"hora": hora, "disponivel": is_slot_available(medico_id, data, hora)}
            for hora in horarios
        ],
    })


@app.route("/api/medicos/<int:medico_id>", methods=["GET", "DELETE"])
def medico_por_id(medico_id):
    medico = next((m for m in DATA.get("medicos", []) if m.get("id") == medico_id), None)
    if medico is None:
        return jsonify({"erro": "Médico não encontrado"}), 404
    if request.method == "DELETE":
        DATA["medicos"].remove(medico)
        save_data()
        return jsonify({"mensagem": "Médico excluído"})
    return jsonify(medico)


@app.route("/api/pacientes/<int:paciente_id>", methods=["GET", "DELETE"])
def paciente_por_id(paciente_id):
    paciente = next((p for p in DATA.get("pacientes", []) if p.get("id") == paciente_id), None)
    if paciente is None:
        return jsonify({"erro": "Paciente não encontrado"}), 404
    if request.method == "DELETE":
        DATA["pacientes"].remove(paciente)
        save_data()
        return jsonify({"mensagem": "Paciente excluído"})
    return jsonify(paciente)


@app.route("/api/agenda", methods=["GET", "POST"])
def agenda():
    if request.method == "GET":
        return jsonify([normalize_appointment(item) for item in DATA.get("agendamentos", [])])

    payload = request.get_json(silent=True) or {}
    agendamento = dict(payload)
    agendamento.setdefault("id", max((a.get("id", 0) for a in DATA.get("agendamentos", [])), default=0) + 1)
    DATA.setdefault("agendamentos", []).append(agendamento)
    save_data()
    return jsonify(normalize_appointment(agendamento)), 201


@app.route("/api/agenda/<int:agendamento_id>", methods=["DELETE"])
def excluir_agendamento(agendamento_id):
    agendamento = next((a for a in DATA.get("agendamentos", []) if a.get("id") == agendamento_id), None)
    if agendamento is None:
        return jsonify({"erro": "Agendamento não encontrado"}), 404

    DATA["agendamentos"].remove(agendamento)
    save_data()
    return jsonify({"mensagem": "Agendamento excluído", "agendamento": normalize_appointment(agendamento)})


@app.route("/api/usuarios/<int:usuario_id>", methods=["GET"])
def usuario_por_id(usuario_id):
    usuario = next((u for u in DATA.get("usuarios", []) if u.get("id") == usuario_id), None)
    if usuario is None:
        return jsonify({"erro": "Usuário não encontrado"}), 404
    retorno = dict(usuario)
    retorno.pop("senha", None)
    return jsonify(retorno)


@app.route("/api/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok", "service": "callmed-api"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
