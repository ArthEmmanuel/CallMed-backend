import re
import unicodedata


RULES_VERSION = "draft-1"

SOURCES = {
    "samu_192": "https://www.gov.br/saude/pt-br/composicao/saes/samu-192",
    "stroke": "https://www.cdc.gov/stroke/signs-symptoms/index.html",
    "chest_pain": "https://www.nhs.uk/symptoms/chest-pain/",
    "anaphylaxis": "https://www.nhs.uk/conditions/anaphylaxis/",
    "emotional_support": "https://cvv.org.br/",
}

CATEGORY_KEYWORDS = {
    "respiratorio": (
        "falta de ar", "tosse", "chiado", "respirar", "respiracao",
        "congestao", "catarro", "febre",
    ),
    "digestivo": (
        "dor abdominal", "dor na barriga", "nausea", "vomito", "diarreia",
        "prisao de ventre", "azia", "estomago",
    ),
    "neurologico": (
        "dor de cabeca", "enxaqueca", "tontura", "formigamento",
        "fraqueza", "visao", "fala",
    ),
    "pele": ("pele", "mancha", "coceira", "ferida", "erupcao", "acne"),
    "urinario": (
        "urina", "urinario", "ardor ao urinar", "dor ao urinar",
        "frequencia urinaria",
    ),
    "saude_mental": (
        "ansiedade", "depressao", "angustia", "tristeza", "panico",
        "insonia", "sofrimento emocional",
    ),
    "saude_da_mulher": (
        "menstruacao", "menstrual", "gravidez", "gestacao", "vaginal",
    ),
    "infantil": ("crianca", "crianca", "bebe", "infantil"),
    "ocular": ("olho", "visao", "vista", "ocular"),
    "otologico": ("ouvido", "audicao", "zumbido", "dor de ouvido"),
    "musculoesqueletico": (
        "joelho", "ombro", "costas", "coluna", "articulacao", "musculo",
        "osso", "torcao", "entorse",
    ),
    "dor": ("dor", "doendo", "dolorido", "dolorida"),
}

FOLLOW_UP_FIELDS = {
    "respiratorio": ("duracao", "intensidade", "evolucao", "associados"),
    "digestivo": ("duracao", "intensidade", "evolucao", "associados"),
    "neurologico": ("duracao", "evolucao", "associados"),
    "pele": ("localizacao", "duracao", "associados", "evolucao"),
    "urinario": ("duracao", "associados", "evolucao"),
    "saude_mental": ("duracao", "impacto"),
    "saude_da_mulher": ("duracao", "associados"),
    "infantil": ("duracao", "evolucao", "associados"),
    "ocular": ("duracao", "evolucao", "associados"),
    "otologico": ("duracao", "evolucao", "associados"),
    "musculoesqueletico": (
        "localizacao", "duracao", "intensidade", "impacto",
    ),
    "dor": ("localizacao", "duracao", "intensidade", "evolucao"),
    "geral": ("duracao", "evolucao", "impacto"),
}

QUESTIONS = {
    "localizacao": "Em que parte do corpo você sente isso?",
    "duracao": "Há quanto tempo isso começou? Pode dizer um período aproximado.",
    "intensidade": (
        "Como você percebe a intensidade: leve, moderada ou intensa? "
        "Se preferir, pode usar uma escala de 0 a 10."
    ),
    "evolucao": "Desde que começou, está melhorando, piorando ou continua igual?",
    "associados": (
        "Além da queixa principal, que outros sintomas percebeu? "
        "Você também pode responder “nenhum” ou “não sei”."
    ),
    "impacto": (
        "Isso está atrapalhando o sono, a alimentação ou suas atividades? "
        "O que está mais afetado?"
    ),
}

SPECIALTY_RULES = {
    "otologico": ("otorrinolaringologia", "otorrino"),
    "pele": ("dermatologia",),
    "musculoesqueletico": ("ortopedia",),
    "ocular": ("oftalmologia",),
    "digestivo": ("gastroenterologia",),
    "urinario": ("urologia", "clinica medica", "clinica geral"),
    "neurologico": ("neurologia", "clinica medica", "clinica geral"),
    "respiratorio": ("pneumologia", "clinica medica", "clinica geral"),
    "saude_mental": ("psiquiatria",),
    "saude_da_mulher": ("ginecologia",),
    "infantil": ("pediatria",),
    "dor": ("clinica medica", "clinica geral"),
    "geral": ("clinica medica", "clinica geral"),
}

URGENT_RULES = (
    {
        "id": "chest_pain_with_concerning_symptoms",
        "label": "Dor ou pressão no peito com outros sintomas preocupantes",
        "source": SOURCES["chest_pain"],
        "signals": (
            "dor no peito", "pressao no peito", "aperto no peito",
        ),
        "associated": (
            "falta de ar", "suor frio", "suando", "suor excessivo",
            "tontura", "desmaio", "nausea", "dor no braco", "dor na mandibula",
        ),
    },
    {
        "id": "severe_breathing_difficulty",
        "label": "Dificuldade intensa para respirar",
        "source": SOURCES["chest_pain"],
        "signals": (
            "nao consigo respirar", "nao consegue respirar",
            "dificuldade intensa para respirar",
            "dificuldade grave para respirar", "estou sufocando",
            "labios azulados", "labios arroxeados",
        ),
    },
    {
        "id": "possible_stroke_signs",
        "label": "Alteração súbita de força, fala, face, visão ou equilíbrio",
        "source": SOURCES["stroke"],
        "signals": (
            "fraqueza de um lado", "fraqueza em um lado",
            "um lado do corpo", "rosto torto", "boca torta",
            "face caída", "fala enrolada", "dificuldade para falar",
            "nao consigo falar", "perda subita da visao",
            "visao subitamente", "perdi o equilibrio de repente",
        ),
        "onset": ("de repente", "subitamente", "agora", "inicio subito"),
    },
    {
        "id": "unconscious_or_seizing",
        "label": "Perda de consciência ou convulsão em curso",
        "source": SOURCES["samu_192"],
        "signals": (
            "nao acorda", "nao consigo acordar", "inconsciente agora",
            "desmaiou agora", "estou desmaiando", "convulsao agora",
            "convulsionando", "crise convulsiva agora",
        ),
    },
    {
        "id": "severe_bleeding",
        "label": "Sangramento intenso ou que não para",
        "source": SOURCES["samu_192"],
        "signals": (
            "sangramento intenso", "sangrando muito", "sangue nao para",
            "nao para de sangrar", "hemorragia intensa",
        ),
    },
    {
        "id": "possible_severe_allergic_reaction",
        "label": "Inchaço súbito na boca ou garganta com dificuldade respiratória",
        "source": SOURCES["anaphylaxis"],
        "signals": (
            "lingua inchada", "garganta inchada", "labios inchados",
            "inchaco na lingua", "inchaco na garganta", "inchaco nos labios",
        ),
        "associated": (
            "falta de ar", "dificuldade para respirar",
            "dificuldade para engolir", "nao consigo engolir",
        ),
    },
    {
        "id": "immediate_self_harm_risk",
        "label": "Risco imediato de ferir a si ou outra pessoa",
        "source": SOURCES["samu_192"],
        "signals": (
            "vou me matar", "vou tirar minha vida", "vou me ferir agora",
            "plano para me matar", "vou machucar alguem agora",
            "risco de machucar alguem agora",
        ),
    },
)

URGENT_RESPONSE = (
    "O que você descreveu pode precisar de atendimento imediato. Esta conversa "
    "não consegue avaliar a gravidade nem substituir um profissional. "
    "Interrompa a triagem e procure um serviço de emergência agora ou ligue "
    "192 (SAMU) no Brasil. Não espere uma consulta ou resposta pelo aplicativo."
)

SAFETY_SCREEN_QUESTION = (
    "Antes de continuar: você está com algum sinal grave agora, como dor ou "
    "pressão no peito junto com falta de ar, dificuldade intensa para respirar, "
    "fraqueza súbita de um lado ou alteração súbita da fala, desmaio, convulsão, "
    "sangramento intenso, inchaço na boca ou garganta com dificuldade para "
    "respirar, ou risco imediato de se ferir? Responda sim ou não; se sim, "
    "diga qual."
)


def normalize_text(value):
    normalized = unicodedata.normalize("NFD", str(value).casefold())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", normalized)).strip()


def _phrase_occurs(text, phrase):
    normalized = normalize_text(text)
    target = normalize_text(phrase)
    for match in re.finditer(rf"(?<!\w){re.escape(target)}(?!\w)", normalized):
        prefix = normalized[max(0, match.start() - 70):match.start()]
        if re.search(r"\b(?:nao|sem|nunca|nega|negou)\b(?:\W+\w+){0,4}\W*$", prefix):
            continue
        return True
    return False


def detect_urgent_signals(text):
    alerts = []
    for rule in URGENT_RULES:
        signal_present = any(
            _phrase_occurs(text, signal) for signal in rule["signals"]
        )
        if not signal_present:
            continue
        associated = rule.get("associated")
        if associated and not any(
            _phrase_occurs(text, signal) for signal in associated
        ):
            continue
        onset = rule.get("onset")
        if onset and not any(_phrase_occurs(text, signal) for signal in onset):
            continue
        alerts.append(
            {
                "codigo": rule["id"],
                "sinal": rule["label"],
                "fonte": rule["source"],
            }
        )
    return alerts


def classify_categories(text):
    normalized = normalize_text(text)
    categories = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(
            re.search(
                rf"(?<!\w){re.escape(normalize_text(keyword))}(?!\w)",
                normalized,
            )
            for keyword in keywords
        ):
            categories.append(category)
    return categories or ["geral"]


def infer_fields(text):
    normalized = normalize_text(text)
    fields = {}

    duration_patterns = (
        r"\b(?:ha|faz)\s+.{1,35}?\b(?:segundo|segundos|minuto|minutos|hora|horas|dia|dias|semana|semanas|mes|meses|ano|anos)\b",
        r"\b(?:desde ontem|desde hoje|desde esta manha|desde a semana passada)\b",
    )
    for pattern in duration_patterns:
        match = re.search(pattern, normalized)
        if match:
            fields["duracao"] = match.group(0)
            break

    intensity = re.search(
        r"\b(?:nota|intensidade)\s*(?:de)?\s*(10|[0-9])"
        r"(?:\s*(?:de|/)\s*10)?\b",
        normalized,
    )
    if intensity:
        fields["intensidade"] = intensity.group(1) + "/10"
    else:
        for value in ("leve", "moderada", "moderado", "intensa", "intenso"):
            if _phrase_occurs(normalized, value):
                fields["intensidade"] = value
                break

    for value, phrases in {
        "melhorando": (
            "esta melhorando", "melhorando", "melhorou", "esta passando",
        ),
        "piorando": (
            "esta piorando", "piorando", "piorou", "ficou mais forte",
        ),
        "estavel": ("continua igual", "esta igual", "sem mudanca"),
    }.items():
        if any(_phrase_occurs(normalized, phrase) for phrase in phrases):
            fields["evolucao"] = value
            break

    location_terms = (
        "cabeca", "peito", "barriga", "abdomen", "ouvido", "garganta",
        "nariz", "olho", "costas", "coluna", "joelho", "ombro", "braco",
        "perna", "mao", "pe", "pele", "articulacao",
    )
    locations = [
        term for term in location_terms
        if _phrase_occurs(normalized, term)
    ]
    if locations:
        fields["localizacao"] = locations

    body_locations = {
        "abdomen", "braco", "barriga", "cabeca", "coluna", "garganta",
        "joelho", "mao", "nariz", "olho", "ombro", "ouvido", "pe",
        "pele", "perna", "peito",
    }
    occurrences = []
    for keywords in CATEGORY_KEYWORDS.values():
        for keyword in keywords:
            match = re.search(
                rf"(?<!\w){re.escape(normalize_text(keyword))}(?!\w)",
                normalized,
            )
            if match:
                occurrences.append(
                    (
                        match.start(),
                        match.end(),
                        normalize_text(keyword),
                    )
                )
    occurrences.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    non_overlapping = []
    for occurrence in occurrences:
        if non_overlapping and occurrence[0] < non_overlapping[-1][1]:
            continue
        non_overlapping.append(occurrence)
    primary_term = next(
        (term for _, _, term in non_overlapping if term not in body_locations),
        None,
    )
    associated = {
        term
        for _, _, term in non_overlapping
        if term not in body_locations and term != primary_term
    }
    if associated:
        fields["sintomas_associados"] = sorted(associated)

    return fields


def suggest_registered_specialties(categories, catalog, doctors):
    registered = []
    for record in catalog:
        name = (
            record.get("nome")
            or record.get("name")
            or record.get("especialidade")
        )
        if isinstance(name, str) and name.strip():
            registered.append(name.strip())
    for doctor in doctors:
        name = doctor.get("especialidade")
        if isinstance(name, str) and name.strip():
            registered.append(name.strip())

    unique_registered = list(dict.fromkeys(registered))
    suggestions = []
    for category in categories:
        aliases = SPECIALTY_RULES.get(category, ())
        for registered_name in unique_registered:
            normalized_name = normalize_text(registered_name)
            if any(
                normalized_name == normalize_text(alias)
                for alias in aliases
            ):
                if registered_name not in suggestions:
                    suggestions.append(registered_name)

    return {
        "sugeridas_preliminarmente": suggestions,
        "cadastradas_no_sistema": unique_registered,
        "regra": RULES_VERSION,
        "estado_validacao_clinica": "requer_revisao_profissional",
    }
