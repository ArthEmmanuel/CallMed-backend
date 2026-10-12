from typing import Any, Protocol


class DataRepository(Protocol):
    def get_all(self, collection: str) -> list[dict[str, Any]]:
        ...

    def get_by_id(
        self, collection: str, record_id: int | str
    ) -> dict[str, Any] | None:
        ...

    def find_by_field(
        self, collection: str, field: str, value: Any
    ) -> dict[str, Any] | None:
        ...

    def insert(self, collection: str, record: dict[str, Any]) -> dict[str, Any]:
        ...

    def replace(self, collection: str, record: dict[str, Any]):
        ...

    def delete(self, collection: str, record_id: int | str) -> bool:
        ...

    def delete_by_field(self, collection: str, field: str, value: Any) -> int:
        ...

    def get_document(self, collection: str) -> dict[str, Any]:
        ...

    def save_document(self, collection: str, document: dict[str, Any]):
        ...

    def replace_document(self, collection: str, document: dict[str, Any]):
        ...

    def delete_document(self, collection: str) -> bool:
        ...
