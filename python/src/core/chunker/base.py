from abc import ABC, abstractmethod


class Chunker(ABC):
    @abstractmethod
    def chunk(self, text: str, doc_id: str) -> list:
        pass
