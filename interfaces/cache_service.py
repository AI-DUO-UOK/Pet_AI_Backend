from abc import ABC, abstractmethod
from typing import Optional, Any

class ICacheService(ABC):
    """Interface for Caching Service"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, expire_seconds: int = 3600):
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def delete_by_prefix(self, prefix: str):
        pass
