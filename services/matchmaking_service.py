from repositories.data_repository import DataRepository
from services.appointment_service import AppointmentService
from services.errors import ServiceError
from services.helpers import as_id, normalize_text


MATCH_SPECIALTY_RULES = {
    "cardiologia": [
        "cardiologia",
        "coracao",
        "pressao",
        "dor no peito",
        "palpitacao",
        "falta de ar",
        "arritmia",
        "taquicardia",
    ],
    "dermatologia": ["dermatologia", "pele", "mancha", "coceira", "erupcao", "acne"],
    "pediatria": ["pediatria", "crianca", "bebe", "infantil", "febre infantil"],
    "ortopedia": [
        "ortopedia",
        "osso",
        "fratura",
        "joelho",
        "coluna",
        "ombro",
        "entorse",
    ],
    "oftalmologia": [
        "oftalmologia",
        "olho",
        "visao",
        "miopia",
        "vista",
        "conjuntivite",
    ],
    "psiquiatria": ["psiquiatria", "ansiedade", "depressao", "estresse", "insonia"],
    "ginecologia": ["ginecologia", "menstruacao", "gravidez", "gestacao"],
    "otorrinolaringologia": [
        "otorrino",
        "garganta",
        "nariz",
        "ouvido",
        "sinusite",
        "otite",
    ],
    "neurologia": [
        "neurologia",
        "dor de cabeca",
        "enxaqueca",
        "tontura",
        "formigamento",
    ],
    "endocrinologia": ["endocrinologia", "diabetes", "hormonal", "tireoide"],
    "urologia": ["urologia", "urina", "urinario", "rim", "prostata", "calculo renal"],
    "alergologia": ["alergologia", "alergia", "asma", "rinite alergica", "dermatite"],
    "nutrologia": [
        "nutrologia",
        "alimentacao",
        "nutricao",
        "peso",
        "obesidade",
        "dieta",
    ],
    "geriatria": ["geriatria", "idoso", "envelhecimento", "quedas", "memoria"],
    "clinica geral": [
        "febre",
        "gripe",
        "resfriado",
        "dor",
        "mal estar",
        "cansaco",
        "rotina",
        "checkup",
    ],
}


class MatchmakingService:
    def __init__(self, repository: DataRepository, appointments: AppointmentService):
        self.repository = repository
        self.appointments = appointments

    def build_response(self, patient_id, need, symptoms=None, date=None, hour=None):
        patients = self.repository.get_all("pacientes")
        patient_id = as_id(patient_id)
        patient = next(
            (item for item in patients if as_id(item.get("id")) == patient_id),
            None,
        )
        if patient is None:
            raise ServiceError("Paciente não encontrado", 404)

        matched_specialties = self._get_specialty_matches(need, symptoms)
        top_specialties = [specialty for specialty, _ in matched_specialties[:3]]
        doctors = []
        for doctor in self.repository.get_all("medicos"):
            specialty = normalize_text(doctor.get("especialidade", ""))
            score = 0
            specialty_hits = []

            for target_specialty, specialty_score in matched_specialties:
                target = normalize_text(target_specialty)
                if target in specialty or specialty in target:
                    specialty_hits.append((target_specialty, specialty_score))
                    score += 110 + specialty_score
                elif specialty == "clinica geral" and target == "clinica geral":
                    score += 35 + specialty_score

            if any(
                term in normalize_text(need)
                for term in ("dor", "febre", "gripe", "cansaco", "mal estar")
            ) and "clinica geral" in specialty:
                score += 10

            if date and hour:
                available = self.appointments.is_slot_available(
                    doctor.get("id"), date, hour
                )
                score += 40 if available else -150
            else:
                available = True

            if "status" in doctor and str(doctor.get("status", "")).lower() == "ativo":
                score += 5

            if score > 0 and available:
                doctors.append(
                    {
                        "id": doctor.get("id"),
                        "nome": doctor.get("nome"),
                        "especialidade": doctor.get("especialidade"),
                        "crm": doctor.get("crm"),
                        "telefone": doctor.get("telefone"),
                        "score": score,
                        "disponibilidade": {"data": date, "hora": hour},
                        "disponivel": available,
                        "prioridade": (
                            "especialidade_e_disponibilidade"
                            if date and hour
                            else "especialidade"
                        ),
                        "specialty_hits": specialty_hits,
                    }
                )

        recommendations = sorted(
            doctors, key=lambda item: item["score"], reverse=True
        )[:5]
        return {
            "paciente": {"id": patient.get("id"), "nome": patient.get("nome")},
            "necessidade": need,
            "triagem": {
                "sintomas": (
                    symptoms
                    if isinstance(symptoms, list)
                    else [symptoms]
                    if symptoms
                    else []
                ),
                "especialidades_sugeridas": top_specialties,
                "mensagem": (
                    "Triagem automatizada concluída. Foram identificadas "
                    "especialidades mais compatíveis com a necessidade do paciente."
                ),
            },
            "recomendacoes": recommendations,
        }

    @staticmethod
    def _get_specialty_matches(need, symptoms=None):
        search_terms = []
        if need:
            search_terms.append(normalize_text(need))
        if symptoms:
            if isinstance(symptoms, str):
                search_terms.append(normalize_text(symptoms))
            else:
                search_terms.extend(normalize_text(item) for item in symptoms)

        all_terms = " ".join(search_terms)
        matches = []
        for specialty, keywords in MATCH_SPECIALTY_RULES.items():
            score = 0
            for keyword in keywords:
                if keyword in all_terms:
                    score += 30 if keyword == normalize_text(need) else 20
            if score > 0:
                matches.append((specialty, score))
        if not matches:
            matches.append(("clinica geral", 10))
        return sorted(matches, key=lambda item: item[1], reverse=True)
