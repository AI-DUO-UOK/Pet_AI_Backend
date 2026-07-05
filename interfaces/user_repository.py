from abc import ABC, abstractmethod
from typing import Dict, Optional

class IUserRepository(ABC):
    """Interface for UserRepository"""

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def update_user(self, user_id: str, updates: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_owner_profile(self, user_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def insert_owner_profile(self, owner_data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def update_owner_profile(self, user_id: str, updates: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def insert_notification(self, payload: Dict) -> Optional[Dict]:
        pass
