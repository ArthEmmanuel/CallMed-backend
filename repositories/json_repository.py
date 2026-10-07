import json
from copy import deepcopy
from pathlib import Path
from typing import Any


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


class JsonRepository:
    """Persistência local temporária.

    A integração externa ainda não foi definida.
    """

    def __init__(self, data_file: Path):
        self.data_file = Path(data_file)
        self.data = self._load()

    def _load(self):
        if self.data_file.exists():
            with self.data_file.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            data = loaded if isinstance(loaded, dict) else {}
        else:
            data = {}

        merged = {**deepcopy(DEFAULT_DATA), **data}
        for key, default_value in DEFAULT_DATA.items():
            if not isinstance(default_value, list):
                merged.setdefault(key, deepcopy(default_value))
                continue

            existing = merged.get(key, [])
            if not isinstance(existing, list):
                merged[key] = deepcopy(default_value)
                continue

            existing_by_id = {
                item.get("id")
                for item in existing
                if isinstance(item, dict) and item.get("id") is not None
            }
            for item in default_value:
                if item.get("id") is not None and item["id"] not in existing_by_id:
                    existing.append(deepcopy(item))
                    existing_by_id.add(item["id"])
            merged[key] = existing

        if not self.data_file.exists():
            self.data = merged
            self._write()
        return merged

    def _write(self):
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        with self.data_file.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=2, ensure_ascii=False)

    def get_all(self, collection: str) -> list[dict[str, Any]]:
        return deepcopy(self.data.get(collection, []))

    def save_all(self, collection: str, records: list[dict[str, Any]]):
        self.data[collection] = deepcopy(records)
        self._write()

    def get_document(self, name: str) -> dict[str, Any]:
        return deepcopy(self.data.get(name, {}))

    def save_document(self, name: str, document: dict[str, Any]):
        self.data[name] = deepcopy(document)
        self._write()

    def save_changes(
        self,
        collections: dict[str, list[dict[str, Any]]],
        documents: dict[str, dict[str, Any]] | None = None,
    ):
        for name, records in collections.items():
            self.data[name] = deepcopy(records)
        for name, document in (documents or {}).items():
            self.data[name] = deepcopy(document)
        self._write()
