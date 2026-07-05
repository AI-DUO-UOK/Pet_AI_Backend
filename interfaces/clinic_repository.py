from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class IClinicRepository(ABC):
    """Interface for ClinicRepository"""

    @abstractmethod
    def insert_clinic(self, clinic_data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_by_id(self, clinic_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_all_clinics(self) -> List[Dict]:
        pass

    @abstractmethod
    def get_public_clinics(self) -> List[Dict]:
        pass

    @abstractmethod
    def update_clinic(self, clinic_id: str, updates: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def reject_clinic(self, clinic_id: str, updates: Dict) -> Optional[Dict]:
        pass
