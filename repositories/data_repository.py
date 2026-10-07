from typing import Any, Protocol


class DataRepository(Protocol):
    def get_all(self, collection: str) -> list[dict[str, Any]]:
        ...

    def save_all(self, collection: str, records: list[dict[str, Any]]):
        ...

    def get_document(self, name: str) -> dict[str, Any]:
        ...

    def save_document(self, name: str, document: dict[str, Any]):
        ...

    def save_changes(
        self,
        collections: dict[str, list[dict[str, Any]]],
        documents: dict[str, dict[str, Any]] | None = None,
    ):
        ...
