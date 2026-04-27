from abc import ABC, abstractmethod


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> list:
        pass
