from typing import Any

from pymongo import MongoClient

from repositories.data_repository import DataRepository


COLLECTION_NAMES = {
    "usuarios": "usuarios",
    "pacientes": "pacientes",
    "medicos": "medicos",
    "clinicas": "clinicas",
    "agendamentos": "agendamentos",
    "historico": "logs",
    "config": "configuracoes",
}


class MongoRepository(DataRepository):
    def __init__(self, mongo_uri: str, database_name: str):
        if not mongo_uri:
            raise RuntimeError(
                "MONGO_URI não definida. Configure-a no ambiente do backend."
            )
        self.client = MongoClient(mongo_uri)
        self.database = self.client[database_name]

    def get_all(self, collection: str) -> list[dict[str, Any]]:
        return [
            self._without_mongo_id(document)
            for document in self._collection(collection).find()
        ]

    def insert(self, collection: str, record: dict[str, Any]):
        self._collection(collection).insert_one(dict(record))

    def replace(self, collection: str, record: dict[str, Any]):
        if "id" not in record:
            raise ValueError("O registro precisa conter o campo numérico 'id'.")
        self._collection(collection).replace_one(
            {"id": record["id"]},
            dict(record),
            upsert=True,
        )

    def delete(self, collection: str, record_id: int) -> bool:
        result = self._collection(collection).delete_one({"id": record_id})
        return result.deleted_count > 0

    def get_document(self, collection: str) -> dict[str, Any]:
        document = self._collection(collection).find_one()
        if document is None:
            return {}
        return self._without_mongo_id(document)

    def save_document(self, collection: str, document: dict[str, Any]):
        target = self._collection(collection)
        existing = target.find_one()
        if existing is None:
            target.insert_one(dict(document))
            return
        target.update_one(
            {"_id": existing["_id"]},
            {"$set": dict(document)},
        )

    def _collection(self, name: str):
        try:
            collection_name = COLLECTION_NAMES[name]
        except KeyError as error:
            raise ValueError(f"Collection não configurada: {name}") from error
        return self.database[collection_name]

    @staticmethod
    def _without_mongo_id(document: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in document.items() if key != "_id"}
