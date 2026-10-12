import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from pymongo import MongoClient


MODULE_NAME = "_callmed_database_connection"
COLLECTION_NAMES = (
    "usuarios",
    "pacientes",
    "medicos",
    "clinicas",
    "especialidades",
    "agendamentos",
    "configuracoes",
    "configuracoes_usuario",
    "logs",
    "triagens",
)


def load_database_module(project_path=None, mongo_uri=None, db_name="callmed"):
    if mongo_uri:
        client = MongoClient(mongo_uri)
        database = client[db_name]
        return SimpleNamespace(
            client=client,
            db=database,
            **{name: database[name] for name in COLLECTION_NAMES},
        )

    configured_path = project_path or os.getenv("DATABASE_PROJECT_PATH")
    if configured_path:
        configured_path = Path(configured_path).expanduser()
        database_file = (
            configured_path
            if configured_path.is_file()
            else configured_path / "database.py"
        )
    else:
        database_file = (
            Path(__file__).resolve().parents[2]
            / "CallMed-Banco-de-dados"
            / "database.py"
        )

    if configured_path and not database_file.is_file():
        raise RuntimeError(
            "Não foi possível localizar database.py do projeto "
            "CallMed-Banco-de-dados. Defina DATABASE_PROJECT_PATH com o "
            "caminho do projeto de dados."
        )

    if not database_file.is_file():
        raise RuntimeError(
            "MONGO_URI não definida e database.py não encontrado. Configure "
            "MONGO_URI no ambiente do host ou disponibilize o projeto de dados."
        )

    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]

    spec = importlib.util.spec_from_file_location(MODULE_NAME, database_file)
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar database.py.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(MODULE_NAME, None)
        raise
    return module
