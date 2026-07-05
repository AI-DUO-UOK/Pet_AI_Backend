"""
Vaccine Reminder Scheduler for Pet AI Backend.
This script is designed to be run daily via cron job at 8:00 AM.

Cron setup (run `crontab -e`):
  0 8 * * * cd /path/to/project && python -m chatbot.reminder_scheduler

Or call via API: POST /api/vaccines/check-reminders
"""

import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_reminder_check():
    """
    Run the vaccine reminder check.
    Queries all vaccination records with upcoming next_due_date,
    calculates days remaining, and creates notifications if not already sent.
    """
    try:
        from services.vaccine_service import VaccineService
        from repositories.vaccine_repository import VaccineRepository
        from repositories.user_repository import UserRepository
        
        logger.info(f"=== Vaccine Reminder Check Started at {datetime.now().isoformat()} ===")
        
        vaccine_service = VaccineService(
            vaccine_repo=VaccineRepository(),
            user_repo=UserRepository()
        )
        result = vaccine_service.check_and_send_reminders()
        
        if result.get("success"):
            count = result.get("notifications_created", 0)
            logger.info(f"Reminder check complete. Created {count} new notifications.")
        else:
            logger.error(f"Reminder check failed: {result.get('error')}")
        
        logger.info(f"=== Vaccine Reminder Check Finished at {datetime.now().isoformat()} ===")
        
        return result
        
    except Exception as e:
        logger.error(f"Reminder scheduler error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    """
    Run directly: python -m chatbot.reminder_scheduler
    """
    result = run_reminder_check()
    sys.exit(0 if result.get("success") else 1)