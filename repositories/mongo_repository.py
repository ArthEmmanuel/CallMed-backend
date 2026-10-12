import re
from typing import Any

from bson import ObjectId

from repositories.data_repository import DataRepository


COLLECTION_NAMES = {
    "usuarios": "usuarios",
    "pacientes": "pacientes",
    "medicos": "medicos",
    "clinicas": "clinicas",
    "especialidades": "especialidades",
    "agendamentos": "agendamentos",
    "historico": "logs",
    "config": "configuracoes",
    "configuracoes_usuario": "configuracoes_usuario",
    "triagens": "triagens",
}


class MongoRepository(DataRepository):
    def __init__(self, database_module):
        self.collections = {
            name: getattr(database_module, collection_name)
            for name, collection_name in COLLECTION_NAMES.items()
        }

    def get_all(self, collection: str) -> list[dict[str, Any]]:
        return [
            self._serialize(document)
            for document in self._collection(collection).find({})
        ]

    def get_by_id(
        self, collection: str, record_id: int | str
    ) -> dict[str, Any] | None:
        document = self._collection(collection).find_one(
            self._id_filter(record_id)
        )
        return self._serialize(document) if document is not None else None

    def find_by_field(
        self, collection: str, field: str, value: Any
    ) -> dict[str, Any] | None:
        document = self._collection(collection).find_one(
            self._field_filter(field, value)
        )
        return self._serialize(document) if document is not None else None

    def insert(self, collection: str, record: dict[str, Any]) -> dict[str, Any]:
        document = {
            key: value for key, value in record.items() if key != "_id"
        }
        result = self._collection(collection).insert_one(document)
        if "id" not in document:
            document["id"] = str(result.inserted_id)
        return document

    def replace(self, collection: str, record: dict[str, Any]):
        if "id" not in record:
            raise ValueError("O registro precisa conter o campo 'id'.")
        target = self._collection(collection)
        query = self._id_filter(record["id"])
        existing = target.find_one(query)
        if existing is None:
            return False
        replacement = {
            key: value for key, value in record.items() if key != "_id"
        }
        if "_id" in existing:
            replacement["_id"] = existing["_id"]
        result = target.replace_one(
            {"_id": existing["_id"]} if "_id" in existing else query,
            replacement,
        )
        return result.modified_count > 0 or result.matched_count > 0

    def delete(self, collection: str, record_id: int | str) -> bool:
        result = self._collection(collection).delete_one(
            self._id_filter(record_id)
        )
        return result.deleted_count > 0

    def delete_by_field(self, collection: str, field: str, value: Any) -> int:
        result = self._collection(collection).delete_many(
            self._field_filter(field, value)
        )
        return result.deleted_count

    def get_document(self, collection: str) -> dict[str, Any]:
        document = self._collection(collection).find_one()
        if document is None:
            return {}
        return self._serialize(document)

    def save_document(self, collection: str, document: dict[str, Any]):
        target = self._collection(collection)
        existing = target.find_one()
        if existing is None:
            target.insert_one(
                {key: value for key, value in document.items() if key != "_id"}
            )
            return
        target.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    key: value
                    for key, value in document.items()
                    if key != "_id"
                }
            },
        )

    def replace_document(self, collection: str, document: dict[str, Any]):
        target = self._collection(collection)
        existing = target.find_one()
        replacement = {
            key: value for key, value in document.items() if key != "_id"
        }
        if existing is None:
            target.insert_one(replacement)
            return
        if "_id" in existing:
            replacement["_id"] = existing["_id"]
            target.replace_one({"_id": existing["_id"]}, replacement)
            return
        target.replace_one({}, replacement)

    def delete_document(self, collection: str) -> bool:
        result = self._collection(collection).delete_one({})
        return result.deleted_count > 0

    def _collection(self, name: str):
        try:
            return self.collections[name]
        except KeyError as error:
            raise ValueError(f"Collection não configurada: {name}") from error

    @staticmethod
    def _id_filter(record_id: int | str) -> dict[str, Any]:
        if isinstance(record_id, bool) or record_id is None:
            raise ValueError("ID inválido")
        if isinstance(record_id, int):
            return {"id": record_id}
        value = str(record_id).strip()
        if not value:
            raise ValueError("ID inválido")
        if value.isdecimal():
            return {"id": int(value)}
        if ObjectId.is_valid(value):
            object_id = ObjectId(value)
            return {
                "$or": [
                    {"id": value},
                    {"id": object_id},
                    {"_id": object_id},
                    {"_id": value},
                ]
            }
        return {"id": value}

    @staticmethod
    def _field_filter(field: str, value: Any) -> dict[str, Any]:
        if field == "email" and isinstance(value, str):
            escaped = re.escape(value.strip())
            return {field: {"$regex": f"^{escaped}$", "$options": "i"}}
        if field in {"id", "usuarioId"}:
            values = [value]
            if isinstance(value, str) and value.isdecimal():
                values.append(int(value))
            elif isinstance(value, int) and not isinstance(value, bool):
                values.append(str(value))
            if isinstance(value, str) and ObjectId.is_valid(value):
                values.append(ObjectId(value))
            if len(values) > 1:
                return {"$or": [{field: item} for item in values]}
        return {field: value}

    @classmethod
    def _serialize(cls, document: dict[str, Any]) -> dict[str, Any]:
        serialized = {
            key: cls._serialize_value(value)
            for key, value in document.items()
            if key != "_id"
        }
        if "id" not in serialized and document.get("_id") is not None:
            serialized["id"] = str(document["_id"])
        return serialized

    @classmethod
    def _serialize_value(cls, value: Any) -> Any:
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, dict):
            return {
                key: cls._serialize_value(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._serialize_value(item) for item in value]
        return value
