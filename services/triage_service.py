from datetime import date, datetime, timezone
import re
from uuid import uuid4

from repositories.data_repository import DataRepository
from services.authorization import is_admin, user_role
from services.errors import ServiceError
from services.triage_rules import (
    FOLLOW_UP_FIELDS,
    QUESTIONS,
    RULES_VERSION,
    SAFETY_SCREEN_QUESTION,
    SOURCES,
    URGENT_RESPONSE,
    classify_categories,
    detect_urgent_signals,
    infer_fields,
    normalize_text,
    suggest_registered_specialties,
)


MAX_MESSAGE_LENGTH = 2000
MAX_CONVERSATION_MESSAGES = 100
UNKNOWN_ANSWERS = {"nao sei", "não sei", "prefiro nao dizer", "prefiro não dizer"}
YES_ANSWERS = {"sim", "s", "yes", "tenho", "estou"}
NO_ANSWERS = {"nao", "não", "n", "nenhum", "nenhuma"}
CORRECTABLE_FIELDS = {
    "queixa_principal",
    "localizacao",
    "duracao",
    "intensidade",
    "evolucao",
    "sintomas_associados",
    "impacto",
}


class TriageService:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    def create_conversation(self, actor, patient_id=None):
        if not is_admin(actor) and user_role(actor) != "paciente":
            raise ServiceError("Acesso não autorizado", 403)

        patient = self._resolve_patient(actor, patient_id)
        now = self._now()
        conversation = {
            "id": uuid4().hex,
            "usuarioId": actor.get("id"),
            "pacienteId": patient.get("id"),
            "status": "collecting_symptoms",
            "estado": "collecting_symptoms",
            "aguardando": "queixa_principal",
            "dados": {
                "queixa_principal": None,
                "categorias": [],
                "localizacao": None,
                "duracao": None,
                "intensidade": None,
                "evolucao": None,
                "sintomas_associados": [],
                "impacto": None,
                "sinais_alerta": [],
                "confirmacao_resumo": False,
            },
            "preferencias": {
                "data_desejada": None,
                "periodo": None,
                "modalidade": None,
            },
            "regra_triagem": RULES_VERSION,
            "fontes_seguranca": SOURCES,
            "mensagens": [],
            "criadoEm": now,
            "atualizadoEm": now,
        }
        self._append_message(
            conversation,
            "assistant",
            "Olá! Vou fazer algumas perguntas para entender sua necessidade e "
            "ajudar a identificar uma possível especialidade. Isto não é um "
            "diagnóstico e não substitui avaliação profissional. Se não souber "
            "alguma resposta, pode dizer “não sei”.",
        )
        self._ask(
            conversation,
            "queixa_principal",
            "O que você está sentindo ou qual é a sua principal preocupação?",
        )
        self.repository.insert("triagens", conversation)
        return conversation

    def list_conversations(self, actor):
        conversations = self.repository.get_all("triagens")
        if is_admin(actor):
            return sorted(
                conversations,
                key=lambda item: item.get("criadoEm", ""),
                reverse=True,
            )
        return sorted(
            (
                item
                for item in conversations
                if str(item.get("usuarioId")) == str(actor.get("id"))
            ),
            key=lambda item: item.get("criadoEm", ""),
            reverse=True,
        )

    def get_conversation(self, conversation_id, actor):
        conversation = self._get_owned_conversation(conversation_id, actor)
        return conversation

    def delete_conversation(self, conversation_id, actor):
        conversation = self._get_owned_conversation(conversation_id, actor)
        self.repository.delete("triagens", conversation["id"])
        return {"mensagem": "Conversa de triagem excluída"}

    def correct_conversation(self, conversation_id, payload, actor):
        if not isinstance(payload, dict) or not isinstance(
            payload.get("correcoes"), dict
        ):
            raise ServiceError(
                "Informe os campos corrigidos no objeto 'correcoes'", 400
            )
        corrections = payload["correcoes"]
        if not corrections:
            raise ServiceError("Informe ao menos uma correção", 400)
        invalid_fields = set(corrections) - CORRECTABLE_FIELDS
        if invalid_fields:
            raise ServiceError(
                "Campo não permitido para correção: "
                + ", ".join(sorted(invalid_fields)),
                400,
            )

        conversation = self._get_owned_conversation(conversation_id, actor)
        if conversation.get("estado") == "urgent_referral":
            raise ServiceError(
                "A orientação urgente não pode ser removida pela triagem",
                409,
            )
        data = conversation["dados"]
        if "queixa_principal" in corrections:
            for field in (
                "localizacao",
                "duracao",
                "intensidade",
                "evolucao",
                "sintomas_associados",
                "impacto",
            ):
                data[field] = [] if field == "sintomas_associados" else None
            data.pop("campos_nao_informados", None)
            data.pop("relatou_sem_sintomas_associados", None)
        for field, value in corrections.items():
            if field == "queixa_principal":
                if not isinstance(value, str) or not value.strip():
                    raise ServiceError("A queixa principal é inválida", 400)
                data[field] = value.strip()[:MAX_MESSAGE_LENGTH]
                data["categorias"] = classify_categories(data[field])
                data.update(
                    {
                        key: inferred
                        for key, inferred in infer_fields(data[field]).items()
                        if not data.get(key)
                    }
                )
            elif field == "sintomas_associados":
                if isinstance(value, str):
                    value = [part.strip() for part in re.split(r"[,;]", value)]
                if (
                    not isinstance(value, list)
                    or any(not isinstance(item, str) for item in value)
                ):
                    raise ServiceError(
                        "sintomas_associados deve ser texto ou lista de textos",
                        400,
                    )
                data[field] = [item.strip()[:200] for item in value if item.strip()]
            elif value is not None and (
                not isinstance(value, str) or not value.strip()
            ):
                raise ServiceError(f"{field} deve ser um texto não vazio", 400)
            else:
                data[field] = value.strip()[:200] if isinstance(value, str) else value

        alerts = detect_urgent_signals(
            " ".join(
                value
                for value in (
                    data.get("queixa_principal", ""),
                    *data.get("sintomas_associados", []),
                )
                if isinstance(value, str)
            )
        )
        if alerts:
            return self._set_urgent_referral(conversation, alerts)

        data["confirmacao_resumo"] = False
        conversation["estado"] = "triage_summary"
        conversation["status"] = "triage_summary"
        conversation["resumo"] = self._build_summary(conversation)
        self._ask(
            conversation,
            "confirmar_resumo",
            conversation["resumo"]
            + "\n\nEste resumo está correto? Responda “sim” para continuar "
            "ou “não” e depois indique o que deseja corrigir.",
        )
        return self._save(conversation)

    def send_message(self, conversation_id, text, actor):
        if not isinstance(text, str) or not text.strip():
            raise ServiceError("A mensagem deve ser um texto não vazio", 400)
        text = text.strip()
        if len(text) > MAX_MESSAGE_LENGTH:
            raise ServiceError(
                f"A mensagem deve ter no máximo {MAX_MESSAGE_LENGTH} caracteres",
                400,
            )

        conversation = self._get_owned_conversation(conversation_id, actor)
        if conversation["estado"] in {"urgent_referral", "pending_matchmaking"}:
            raise ServiceError(
                "Esta conversa não aceita novas mensagens neste estado", 409
            )
        if len(conversation["mensagens"]) >= MAX_CONVERSATION_MESSAGES:
            raise ServiceError(
                "Limite de mensagens da conversa atingido", 409
            )

        self._append_message(conversation, "user", text)
        alerts = detect_urgent_signals(text)
        if alerts:
            return self._set_urgent_referral(conversation, alerts)

        if self._respond_to_conversational_intent(conversation, text):
            return self._save(conversation)

        awaiting = conversation.get("aguardando")
        data = conversation["dados"]

        if awaiting == "queixa_principal":
            data["queixa_principal"] = text
            data["categorias"] = classify_categories(text)
            self._extract_unsolicited_fields(data, text)
            self._ask(
                conversation,
                "safety_screen",
                SAFETY_SCREEN_QUESTION,
                state="safety_review",
            )
        elif awaiting == "safety_screen":
            answer = normalize_text(text)
            if answer in YES_ANSWERS or answer.startswith("sim "):
                return self._set_urgent_referral(
                    conversation,
                    [
                        {
                            "codigo": "patient_reported_emergency_signal",
                            "sinal": "Paciente relata sinal grave na verificação de segurança",
                            "fonte": SOURCES["samu_192"],
                        }
                    ],
                )
            if answer not in NO_ANSWERS and not answer.startswith("nao "):
                self._ask(
                    conversation,
                    "safety_screen",
                    "Não consegui entender. Você está com algum dos sinais "
                    "graves que mencionei agora? Responda sim ou não.",
                    state="safety_review",
                )
            else:
                data["verificacao_seguranca"] = "sem_sinal_relatado"
                self._advance_symptoms(conversation)
        elif awaiting in QUESTIONS:
            if self._store_follow_up_answer(conversation, awaiting, text):
                self._extract_unsolicited_fields(data, text)
                self._advance_symptoms(conversation)
        elif awaiting == "confirmar_resumo":
            answer = normalize_text(text)
            if answer in YES_ANSWERS or answer.startswith("sim "):
                data["confirmacao_resumo"] = True
                conversation["preferencias"] = {
                    **conversation["preferencias"],
                    "data_desejada": None,
                    "periodo": None,
                    "modalidade": None,
                }
                self._ask(
                    conversation,
                    "data_desejada",
                    "Qual data você prefere para uma consulta? Informe uma "
                    "data futura no formato AAAA-MM-DD ou diga “sem preferência”.",
                    state="collecting_preferences",
                )
            elif answer in NO_ANSWERS or answer.startswith("nao "):
                self._ask(
                    conversation,
                    "resumo_correcao",
                    "Tudo bem. Diga qual informação está incorreta e qual "
                    "deveria ser o valor correto.",
                    state="triage_summary",
                )
            else:
                self._ask(
                    conversation,
                    "confirmar_resumo",
                    "Responda “sim” se o resumo está correto ou “não” se "
                    "deseja corrigir alguma informação.",
                    state="triage_summary",
                )
        elif awaiting == "resumo_correcao":
            data["queixa_principal"] = text
            data["categorias"] = classify_categories(text)
            data["localizacao"] = None
            data["duracao"] = None
            data["intensidade"] = None
            data["evolucao"] = None
            data["sintomas_associados"] = []
            data["impacto"] = None
            data["confirmacao_resumo"] = False
            self._extract_unsolicited_fields(data, text)
            self._ask(
                conversation,
                "safety_screen",
                SAFETY_SCREEN_QUESTION,
                state="safety_review",
            )
        elif awaiting in {"data_desejada", "periodo", "modalidade"}:
            self._store_preference(conversation, awaiting, text)
        else:
            raise ServiceError("Estado de conversa inválido", 409)

        return self._save(conversation)

    def _respond_to_conversational_intent(self, conversation, text):
        normalized = normalize_text(text)
        awaiting = conversation.get("aguardando")
        response = None
        has_symptom_details = (
            classify_categories(text) != ["geral"] or bool(infer_fields(text))
        )

        if normalized in {
            "oi",
            "ola",
            "bom dia",
            "boa tarde",
            "boa noite",
            "e ai",
        }:
            response = (
                "Oi! Sou um assistente virtual e fico feliz em ajudar. Vou "
                "fazer algumas perguntas curtas para entender o que você "
                "está sentindo. O que está acontecendo?"
            )
        elif any(
            phrase in normalized
            for phrase in (
                "voce faz diagnostico",
                "pode me diagnosticar",
                "qual e meu diagnostico",
                "o que eu tenho",
                "qual doenca eu tenho",
            )
        ) and not (
            awaiting == "queixa_principal" and has_symptom_details
        ):
            response = (
                "Entendo a dúvida, mas não consigo diagnosticar. Posso ajudar "
                "a organizar o que você está sentindo e sugerir, de forma "
                "preliminar, uma especialidade para avaliação profissional."
            )
        elif any(
            phrase in normalized
            for phrase in (
                "qual remedio",
                "qual medicamento",
                "posso tomar",
                "devo tomar",
                "qual antibiotico",
                "me indica um remedio",
            )
        ) and not (
            awaiting == "queixa_principal" and has_symptom_details
        ):
            response = (
                "Não posso indicar remédios nem orientar doses. Isso depende "
                "de uma avaliação profissional e do seu histórico. Se você "
                "já usa algum medicamento, não altere o tratamento por causa "
                "desta conversa."
            )
        elif any(
            phrase in normalized
            for phrase in (
                "como funciona",
                "o que voce pode fazer",
                "quem e voce",
                "voce e medico",
                "isso substitui um medico",
                "quero saber sobre medicos",
                "como agendar",
                "quero marcar consulta",
            )
        ):
            response = (
                "Sou um assistente virtual, não um profissional de saúde. "
                "Posso ajudar a organizar seus sintomas, fazer uma verificação "
                "de segurança e sugerir uma especialidade preliminar. Não faço "
                "diagnósticos, não indico medicamentos e não confirmo "
                "agendamentos."
            )
            if any(
                phrase in normalized
                for phrase in (
                    "quero saber sobre medicos",
                    "como agendar",
                    "quero marcar consulta",
                )
            ):
                response += (
                    " Posso primeiro ajudar com uma triagem preliminar; para "
                    "ver horários e marcar, use a área de agendamentos da "
                    "CallMed."
                )
        elif normalized in {
            "obrigado",
            "obrigada",
            "valeu",
            "muito obrigado",
            "muito obrigada",
        }:
            response = "Por nada. Vamos no seu ritmo."
        elif any(
            phrase in normalized
            for phrase in (
                "nao entendi",
                "pode repetir",
                "repete por favor",
                "o que quer dizer",
                "por que essa pergunta",
            )
        ):
            clarifications = {
                "queixa_principal": (
                    "Quero entender o principal motivo da conversa. O que "
                    "você está sentindo ou o que mais preocupa você?"
                ),
                "safety_screen": (
                    "É uma checagem rápida para não deixar passar algo "
                    "urgente. Você está com algum dos sinais graves que "
                    "mencionei agora? Responda sim ou não."
                ),
                "localizacao": "Em que parte do corpo você sente isso?",
                "duracao": "Quando começou? Pode responder, por exemplo, “hoje” ou “há alguns dias”.",
                "intensidade": "A intensidade parece leve, moderada ou intensa? Se preferir, use uma escala de 0 a 10.",
                "evolucao": "Desde que começou, está melhorando, piorando ou continua igual?",
                "associados": "Além disso, percebeu algum outro sintoma? Você pode dizer “nenhum” ou “não sei”.",
                "impacto": "Isso tem atrapalhado o sono, a alimentação ou suas atividades?",
                "confirmar_resumo": "Confira o resumo acima. Está correto? Responda sim ou não.",
                "resumo_correcao": "Diga qual informação do resumo está incorreta e como devo corrigir.",
                "data_desejada": "Qual data futura você prefere? Pode responder “sem preferência”.",
                "periodo": "Você prefere manhã, tarde ou noite? Também pode dizer “sem preferência”.",
                "modalidade": "Prefere atendimento presencial, online ou sem preferência?",
            }
            response = clarifications.get(
                awaiting,
                "Posso explicar melhor. Qual parte ficou confusa?",
            )

        if response is None:
            return False

        self._append_message(conversation, "assistant", response)
        return True

    def _resolve_patient(self, actor, patient_id):
        if is_admin(actor):
            if patient_id is None:
                raise ServiceError(
                    "pacienteId é obrigatório para iniciar triagem como admin",
                    400,
                )
            patient = self.repository.get_by_id("pacientes", patient_id)
            if patient is None:
                raise ServiceError("Paciente não encontrado", 404)
            return patient

        patient = self.repository.find_by_field(
            "pacientes", "usuarioId", actor.get("id")
        )
        if patient is None:
            patient = self.repository.get_by_id("pacientes", actor.get("id"))
        if patient is None:
            raise ServiceError("Perfil de paciente não encontrado", 404)
        if patient_id is not None and str(patient.get("id")) != str(patient_id):
            raise ServiceError("Acesso não autorizado", 403)
        return patient

    def _get_owned_conversation(self, conversation_id, actor):
        conversation = self.repository.get_by_id("triagens", conversation_id)
        if conversation is None:
            raise ServiceError("Conversa de triagem não encontrada", 404)
        if (
            not is_admin(actor)
            and str(conversation.get("usuarioId")) != str(actor.get("id"))
        ):
            raise ServiceError("Acesso não autorizado", 403)
        return conversation

    def _advance_symptoms(self, conversation):
        data = conversation["dados"]
        known_or_unknown = set(data.get("campos_nao_informados", []))
        follow_ups = []
        for category in data.get("categorias") or ["geral"]:
            for field in FOLLOW_UP_FIELDS.get(category, FOLLOW_UP_FIELDS["geral"]):
                if field not in follow_ups:
                    follow_ups.append(field)
        follow_ups = follow_ups[:4]

        for field in follow_ups:
            value = (
                data.get("sintomas_associados")
                if field == "associados"
                else data.get(field)
            )
            if value not in (None, "", []):
                continue
            if (
                field == "associados"
                and data.get("relatou_sem_sintomas_associados")
            ):
                continue
            if field in known_or_unknown:
                continue
            self._ask(
                conversation,
                field,
                QUESTIONS[field],
                state="asking_followup",
            )
            return

        conversation["estado"] = "triage_summary"
        conversation["status"] = "triage_summary"
        conversation["resumo"] = self._build_summary(conversation)
        self._ask(
            conversation,
            "confirmar_resumo",
            conversation["resumo"]
            + "\n\nEste resumo está correto? Responda “sim” para continuar "
            "ou “não” e depois indique o que deseja corrigir.",
            state="triage_summary",
        )

    def _store_follow_up_answer(self, conversation, field, text):
        data = conversation["dados"]
        normalized = normalize_text(text)
        if normalized in {normalize_text(item) for item in UNKNOWN_ANSWERS}:
            data.setdefault("campos_nao_informados", [])
            if field not in data["campos_nao_informados"]:
                data["campos_nao_informados"].append(field)
            return True

        if field == "intensidade":
            rating = re.search(
                r"\b(10|[0-9])(?:\s*(?:de|/)\s*10)?\b",
                normalized,
            )
            if rating:
                data[field] = f"{rating.group(1)}/10"
            elif any(
                value in normalized
                for value in ("leve", "moderada", "moderado", "intensa", "intenso")
            ):
                data[field] = text[:200]
            else:
                self._ask(
                    conversation,
                    field,
                    "Pode informar uma intensidade de 0 a 10 ou dizer "
                    "“leve”, “moderada” ou “intensa”?",
                    state="asking_followup",
                )
                return False
        elif field == "evolucao":
            data[field] = text[:200]
        elif field == "associados":
            if normalized in {"nenhum", "nenhuma"} or normalized.startswith(
                ("nenhum ", "nenhuma ", "sem outros", "sem mais")
            ):
                data["sintomas_associados"] = []
                data["relatou_sem_sintomas_associados"] = True
            else:
                data["sintomas_associados"] = [
                    item.strip()[:200]
                    for item in re.split(r"[,;]", text)
                    if item.strip()
                ]
        else:
            data[field] = text[:200]

        unknown_fields = data.get("campos_nao_informados", [])
        if field in unknown_fields:
            unknown_fields.remove(field)
        return True

    def _store_preference(self, conversation, field, text):
        normalized = normalize_text(text)
        preferences = conversation["preferencias"]
        if normalized in {"sem preferencia", "tanto faz", "nao sei"}:
            preferences[field] = None
        elif field == "data_desejada":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                raise ServiceError(
                    "Data inválida. Informe no formato AAAA-MM-DD ou "
                    "“sem preferência”.",
                    400,
                )
            try:
                parsed = datetime.strptime(text, "%Y-%m-%d").date()
            except ValueError as error:
                raise ServiceError(
                    "Data inválida. Informe no formato AAAA-MM-DD ou "
                    "“sem preferência”.",
                    400,
                ) from error
            if parsed < date.today():
                raise ServiceError(
                    "A data desejada não pode estar no passado", 400
                )
            preferences[field] = parsed.isoformat()
        elif field == "periodo":
            periods = {
                "manha": "manha",
                "de manha": "manha",
                "tarde": "tarde",
                "a tarde": "tarde",
                "noite": "noite",
                "a noite": "noite",
            }
            if normalized not in periods:
                raise ServiceError(
                    "Período inválido. Escolha manhã, tarde, noite ou "
                    "“sem preferência”.",
                    400,
                )
            preferences[field] = periods[normalized]
        else:
            modalities = {
                "presencial": "presencial",
                "online": "online",
                "virtual": "online",
            }
            if normalized not in modalities:
                raise ServiceError(
                    "Modalidade inválida. Escolha presencial, online ou "
                    "“sem preferência”.",
                    400,
                )
            preferences[field] = modalities[normalized]

        if field == "data_desejada":
            self._ask(
                conversation,
                "periodo",
                "Qual período você prefere: manhã, tarde, noite ou “sem preferência”?",
                state="collecting_preferences",
            )
        elif field == "periodo":
            self._ask(
                conversation,
                "modalidade",
                "Você prefere atendimento presencial, online (se disponível) "
                "ou não tem preferência?",
                state="collecting_preferences",
            )
        else:
            conversation["estado"] = "pending_matchmaking"
            conversation["status"] = "pending_matchmaking"
            conversation["aguardando"] = None
            conversation["matchmaking"] = {
                "estado": "pending_matchmaking",
                "agendamento_confirmado": False,
                "verificacao_disponibilidade_realizada": False,
                "entrada": {
                    "triagemId": conversation["id"],
                    "pacienteId": conversation["pacienteId"],
                    "queixa_principal": conversation["dados"].get(
                        "queixa_principal"
                    ),
                    "sintomas": conversation["dados"],
                    "especialidades": conversation.get(
                        "especialidades_sugeridas", {}
                    ),
                    "preferencias": preferences,
                },
            }
            self._append_message(
                conversation,
                "assistant",
                "Obrigado. Registrei suas preferências e preparei os dados "
                "para uma etapa futura de busca de profissionais. Ainda não "
                "consultei disponibilidade e nenhum agendamento foi feito ou "
                "confirmado. A sugestão de especialidade é preliminar e não "
                "constitui diagnóstico.",
            )

    def _extract_unsolicited_fields(self, data, text):
        inferred = infer_fields(text)
        for field, value in inferred.items():
            if data.get(field) in (None, "", []):
                data[field] = value

    def _build_summary(self, conversation):
        data = conversation["dados"]
        specialties = suggest_registered_specialties(
            data.get("categorias", ["geral"]),
            self.repository.get_all("especialidades"),
            self.repository.get_all("medicos"),
        )
        conversation["especialidades_sugeridas"] = specialties

        parts = [
            "Resumo da triagem — não é um diagnóstico:",
            f"Queixa principal: {data.get('queixa_principal')}.",
        ]
        for label, key in (
            ("Localização", "localizacao"),
            ("Duração", "duracao"),
            ("Intensidade informada", "intensidade"),
            ("Evolução", "evolucao"),
            ("Impacto na rotina", "impacto"),
        ):
            value = data.get(key)
            if value not in (None, "", []):
                parts.append(f"{label}: {self._display(value)}.")
        associated = data.get("sintomas_associados", [])
        if associated:
            parts.append(
                "Outros sintomas relatados: "
                + ", ".join(self._display(item) for item in associated)
                + "."
            )
        elif data.get("relatou_sem_sintomas_associados"):
            parts.append("Outros sintomas: nenhum relatado.")

        suggested = specialties["sugeridas_preliminarmente"]
        if suggested:
            parts.append(
                "Possível especialidade para avaliação profissional: "
                + ", ".join(suggested)
                + ". A indicação é preliminar."
            )
        else:
            parts.append(
                "Não há correspondência de especialidade confirmada no "
                "cadastro para sugerir com estes dados. Considere procurar "
                "avaliação profissional."
            )
        has_clinical_detail = any(
            data.get(field) not in (None, "", [])
            for field in (
                "localizacao",
                "duracao",
                "intensidade",
                "evolucao",
                "sintomas_associados",
                "impacto",
            )
        ) or data.get("relatou_sem_sintomas_associados")
        if not has_clinical_detail:
            parts.append(
                "Ainda há poucos detalhes para uma sugestão preliminar "
                "confiável; procure avaliação profissional."
            )
        if not specialties["cadastradas_no_sistema"]:
            parts.append(
                "O cadastro de especialidades/profissionais está vazio; "
                "nenhuma disponibilidade foi verificada."
            )
        parts.append(
            "A ausência de um alerta identificado não garante ausência de risco."
        )
        return " ".join(parts)

    def _set_urgent_referral(self, conversation, alerts):
        conversation["dados"]["sinais_alerta"] = alerts
        conversation["estado"] = "urgent_referral"
        conversation["status"] = "urgent_referral"
        conversation["aguardando"] = None
        response = URGENT_RESPONSE
        if any(
            alert["codigo"] == "immediate_self_harm_risk"
            for alert in alerts
        ):
            response += (
                " Para apoio emocional, o CVV atende pelo 188; se o risco for "
                "imediato, priorize o 192 ou um serviço de emergência."
            )
        self._append_message(conversation, "assistant", response)
        return self._save(conversation)

    def _ask(self, conversation, field, message, state=None):
        conversation["aguardando"] = field
        if state:
            conversation["estado"] = state
            conversation["status"] = state
        messages = conversation.get("mensagens", [])
        if messages and messages[-1].get("papel") == "user":
            acknowledgements = (
                "Entendi, agradeço por explicar.",
                "Certo, agradeço por me contar.",
                "Agradeço por compartilhar isso comigo.",
            )
            acknowledgement = acknowledgements[
                sum(item.get("papel") == "user" for item in messages)
                % len(acknowledgements)
            ]
            message = f"{acknowledgement}\n\n{message}"
        self._append_message(conversation, "assistant", message)

    @staticmethod
    def _append_message(conversation, role, content):
        conversation.setdefault("mensagens", []).append(
            {
                "papel": role,
                "conteudo": content,
                "criadoEm": TriageService._now(),
            }
        )

    def _save(self, conversation):
        conversation["atualizadoEm"] = self._now()
        self.repository.replace("triagens", conversation)
        return conversation

    @staticmethod
    def _display(value):
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()
