from typing import Any, Protocol


class DataRepository(Protocol):
    def get_all(self, collection: str) -> list[dict[str, Any]]:
        ...

    def insert(self, collection: str, record: dict[str, Any]):
        ...

    def replace(self, collection: str, record: dict[str, Any]):
        ...

    def delete(self, collection: str, record_id: int) -> bool:
        ...

    def get_document(self, collection: str) -> dict[str, Any]:
        ...

    def save_document(self, collection: str, document: dict[str, Any]):
        ...
