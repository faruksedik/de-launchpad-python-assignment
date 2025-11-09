
# main.py
from logger_config import get_logger
import db
import quotes
import email_sender
from datetime import datetime
from config import users_from_database

logger = get_logger("main")

def setup_users():
    """Initialize the database and add new users."""
    logger.info("Starting user setup...")

    try:
        db.init_db()
        users = users_from_database

        for user in users:
            db.add_user(user["email"], user["name"], user["subscription_status"], user["email_frequency"])
            logger.info(f"User {user['email']} added successfully.")

        logger.info("All users added successfully.")
    except Exception as e:
        logger.exception(f"Error setting up users: {e}")
    else:
        logger.info("User setup completed successfully.")

def run_quote_dispatch():
    """Run the main quote fetching and emailing workflow."""
    logger.info("=== Quote Dispatch Workflow Started ===")

    try:
        # Step 1: Fetch quotes from API
        quotes_list = quotes.fetch_quotes()
        if not quotes_list:
            logger.warning("No quotes fetched from ZenQuotes API. Skipping email dispatch.")
            return

        logger.info(f"Fetched {len(quotes_list)} quotes successfully from ZenQuotes API.")

        # Step 2: Send daily quotes
        logger.info("Sending daily quotes...")
        email_sender.send_emails_to_subscribers("daily", quotes_list)
        

        # Step 3: Send weekly quotes
        logger.info("Sending weekly quotes...")
        email_sender.send_emails_to_subscribers("weekly", quotes_list)
        

        # Step 4: Send summary email to admin
        logger.info("Sending summary email to admin...")
        email_sender.send_summary_to_admin()

    except Exception as e:
        logger.exception(f"Unexpected error in quote dispatch workflow: {e}")
    finally:
        logger.info("=== Quote Dispatch Workflow Finished ===")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"App started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Run only one of these depending on what you’re doing:
    setup_users()   # <-- Uncomment this line ONLY when adding new users
    run_quote_dispatch()

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    logger.info(f"App finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')} (Runtime: {elapsed:.2f}s)")
