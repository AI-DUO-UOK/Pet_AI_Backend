from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class IPetRepository(ABC):
    """Interface for PetRepository"""

    @abstractmethod
    def insert_pet(self, pet_data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_by_id(self, pet_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_user_pets(self, user_id: str) -> List[Dict]:
        pass

    @abstractmethod
    def update_pet(self, pet_id: str, updates: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def insert_vaccine_record(self, record_data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_vaccine_records(self, pet_id: str) -> List[Dict]:
        pass
