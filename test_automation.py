import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import app
from src.services.automation_service import AutomationService
from src.models import FacebookAccount

def run_test():
    """Runs the full automation cycle for a test account."""
    with app.app_context():
        # Find a test account to use. Let's use the first active one.
        test_account = FacebookAccount.query.filter_by(is_active=True, is_locked=False).first()

        if not test_account:
            print("No active, unlocked test account found in the database.")
            print("Please run the seeder first.")
            return

        print(f"--- Starting E2E Automation Test for account: {test_account.email} ---")

        automation_service = AutomationService()

        try:
            result = automation_service.run_automation_cycle(test_account.id)
            print("--- Test Run Summary ---")
            print(result)
            print("--- E2E Automation Test Finished Successfully ---")
        except Exception as e:
            print(f"--- E2E Automation Test Failed ---")
            print(f"Error: {e}")

if __name__ == '__main__':
    run_test()
