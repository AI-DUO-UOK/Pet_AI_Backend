from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class IVaccineRepository(ABC):
    """Interface for VaccineRepository"""

    @abstractmethod
    def insert_vaccine_document(self, doc_data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def insert_vaccination_record(self, record_data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_vaccination_records(self, pet_id: str) -> List[Dict]:
        pass

    @abstractmethod
    def get_vaccine_documents(self, pet_id: str) -> List[Dict]:
        pass

    @abstractmethod
    def get_records_with_due_dates(self) -> List[Dict]:
        pass

    @abstractmethod
    def check_notification_log_exists(self, record_id: str, notification_type: str, sent_date: str) -> bool:
        pass

    @abstractmethod
    def log_notification_sent(self, log_data: Dict) -> Optional[Dict]:
        pass
