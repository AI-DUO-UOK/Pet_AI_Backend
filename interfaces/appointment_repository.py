from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class IAppointmentRepository(ABC):
    """Interface for AppointmentRepository"""

    @abstractmethod
    def insert_appointment(self, appointment_data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_by_id(self, appointment_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_user_appointments(self, user_id: str) -> List[Dict]:
        pass

    @abstractmethod
    def get_clinic_appointments(self, clinic_id: str) -> List[Dict]:
        pass

    @abstractmethod
    def update_appointment(self, appointment_id: str, updates: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def insert_review(self, review_data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_reviews_by_clinic(self, clinic_id: str) -> List[Dict]:
        pass

    @abstractmethod
    def get_appointments_by_pet(self, pet_id: str) -> List[Dict]:
        pass
