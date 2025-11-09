# email_sender.py
from datetime import date, datetime
import smtplib
import time
from email.message import EmailMessage
from logger_config import get_logger 
import db 
import quotes
from config import ( 
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    FROM_EMAIL,
    EMAIL_MAX_RETRIES,
    EMAIL_RETRY_BASE_SECONDS,
    ADMIN_EMAIL
)


logger = get_logger("email_sender")


def build_message(to_email, name, quote):
    """
    Build a personalized email message for a user containing their motivational quote.

    This function constructs a plain-text email using the built-in `EmailMessage` class.
    It personalizes the greeting using the recipient's name (if provided) and embeds
    the motivational quote and author in the message body.

    Args:
        to_email (str): Recipient's email address.
        name (str): Recipient's first name or full name (used for greeting). 
            If empty or None, defaults to a generic "Hello" greeting.
        quote (dict): Dictionary containing the quote text and author, in the format:
            {
                "quote": "The only way to do great work is to love what you do.",
                "author": "Steve Jobs"
            }

    Returns:
        EmailMessage: A fully constructed, ready-to-send email message object.

    Logging:
        - DEBUG: Logs before and after building the email message to help trace message creation.
    """
    logger.debug(f"Building email message for recipient '{to_email}'.")
    msg = EmailMessage()
    msg["Subject"] = "Your Daily MindFuel Quote"
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email

    greeting = f"Hi {name}," if name else "Hello,"
    body = f"""{greeting}

Here is your quote for today:

"{quote['quote']}"

— {quote['author']}

Have a great day!
MindFuel Team
"""
    msg.set_content(body)
    logger.debug(f"Email message built successfully for {to_email}.")
    return msg




def send_email_with_retries(user, quote):
    """
    Send a motivational email to a user with retry logic and exponential backoff.

    This function attempts to send an email containing a motivational quote to a user.
    It automatically retries delivery for transient failures (e.g., network or SMTP connection errors)
    using exponential backoff. Permanent failures such as authentication errors or
    invalid recipients stop retries immediately.

    After all attempts (successful or failed), the function logs the final outcome
    in the database via `db.log_email()`.

    Args:
        user (dict): A dictionary representing the user record, containing:
            {
                "id": int,           # User ID in the database
                "email": str,        # Recipient email address
                "name": str | None   # User’s name (optional)
            }
        quote (dict): A dictionary containing the quote text and author, e.g.:
            {
                "quote": "Keep going. Everything you need will come to you at the perfect time.",
                "author": "Unknown"
            }

    Returns:
        bool: 
            - True if the email was sent successfully.
            - False if all retry attempts failed.

    Raises:
        None directly. All exceptions are caught, logged, and retried as appropriate.

    Logging:
        - INFO: When starting to send, on success, and final result.
        - DEBUG: For each individual send attempt.
        - WARNING: When retrying after a failed attempt.
        - ERROR: On failures or SMTP errors.
        - Database logging (via `db.log_email`) records the final status.

    Notes:
        - Retries use **exponential backoff**: each subsequent delay doubles 
          based on `EMAIL_RETRY_BASE_SECONDS`.
        - The number of maximum retries is controlled by `EMAIL_MAX_RETRIES`.
        - Fatal errors (e.g., invalid credentials or recipient rejection) stop
          the retry cycle immediately.
    """
    user_id = user.get("id")
    to_email = user.get("email")
    name = user.get("name") or ""
    
    attempt = 0
    last_error = None
    final_status = "failed"  # Assume failure until proven otherwise
    
    logger.info(f"Preparing to send email to '{to_email}' (User ID: {user_id}).")

    while attempt < EMAIL_MAX_RETRIES:
        attempt += 1
        logger.debug(f"Attempt {attempt}/{EMAIL_MAX_RETRIES} to send email to {to_email}...")

        try:
            msg = build_message(to_email, name, quote)

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
                smtp.ehlo()
                
                if SMTP_PORT == 587:
                    smtp.starttls()
                    smtp.ehlo()

                smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email} (attempt {attempt}).")
            final_status = "sent"
            last_error = None
            break  # Exit loop after success

        except smtplib.SMTPAuthenticationError:
            last_error = "SMTP authentication failed. Check credentials/app password."
            logger.error(f"FATAL: {last_error} (Attempt {attempt})", exc_info=True)
            break

        except smtplib.SMTPRecipientsRefused:
            last_error = f"FATAL: Recipient address {to_email} refused by SMTP server."
            logger.error(f"{last_error} (Attempt {attempt})", exc_info=True)
            break

        except smtplib.SMTPConnectError:
            last_error = "SMTP connection error. Server may be unreachable."
            logger.error(f"TRANSIENT: {last_error} (Attempt {attempt})", exc_info=True)

        except Exception as e:
            last_error = f"Unexpected error: {e}"
            logger.error(f"UNKNOWN: Unexpected error sending email to {to_email} (Attempt {attempt}): {e}", exc_info=True)

        if attempt < EMAIL_MAX_RETRIES:
            sleep_seconds = EMAIL_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
            logger.warning(f"Retrying email to {to_email} in {sleep_seconds:.1f}s (Attempt {attempt} failed with: {last_error}).")
            time.sleep(sleep_seconds)

    db.log_email(user_id, to_email, status=final_status, error=last_error, attempt=attempt)

    if final_status == "failed":
        logger.error(f"FINAL FAILURE: All attempts failed for {to_email}. Last error: {last_error}")
        return False
    
    return True



def send_emails_to_subscribers(frequency: str, quotes_list: list):
    """
    Send quotes to all subscribers based on their email frequency (daily/weekly).

    Steps:
    1. Fetch all active subscribers for the given frequency from the database.
    2. For each subscriber:
        - Select a random quote.
        - Attempt to send the email (with retries).
        - Log the delivery status (sent/failed).
        - Update their `last_email_received_at` timestamp if successful.
    3. Return True if at least one email was sent successfully, False otherwise.

    Args:
        frequency (str): The email frequency to target ('daily' or 'weekly').
        quotes_list (list): List of quotes fetched from the ZenQuotes API.

    Returns:
        bool: True if at least one email sent successfully, False otherwise.
    """
    logger.info(f"Starting {frequency} email delivery process...")

    # Step 1: Fetch subscribers from the database
    try:
        subscribers = db.get_eligible_subscribers(frequency)
        if not subscribers:
            logger.warning(f"No active {frequency} subscribers found.")
            return None
        logger.info(f"Found {len(subscribers)} eligible {frequency} subscribers.")

    except Exception as e:
        logger.exception(f"Error fetching {frequency} subscribers: {e}")
        return False

    success_count = 0
    failure_count = 0

    # Step 2: Send emails to each subscriber
    try:
        for user in subscribers:
            try:
                quote = quotes.get_random_quote(quotes_list)
                send_email_with_retries(user, quote)

                # db.log_email(user["id"], user["email"], status="sent")
                db.update_last_sent(user["id"])
                logger.info(f"Email successfully sent to {user['email']}")
                success_count += 1

            except Exception as e:
                logger.exception(f"Failed to send email to {user['email']}: {e}")
                # db.log_email(user["id"], user["email"], status="failed", error=str(e))
                failure_count += 1

        # Step 3: Log summary
        logger.info(
            f"{frequency.capitalize()} email summary: "
            f"{success_count} sent, {failure_count} failed."
        )

        return True if success_count > 0 else False

    except Exception as e:
        logger.exception(f"Unexpected error during {frequency} email sending: {e}")
        return False


def send_summary_to_admin():
    """
    Compile and email a detailed summary of today's email delivery performance to the admin.

    This function:
        1. Retrieves all email logs for the current day from the database.
        2. Calculates the total number of emails processed, successful deliveries, and failures.
        3. Computes the overall delivery success rate.
        4. Builds a well-formatted summary email body for administrative insight.
        5. Connects to the SMTP server and sends the summary email to the configured admin.
        6. Logs every step, including any encountered exceptions.

    Returns:
        bool: True if the summary email was successfully sent, False otherwise.
    """
    today = date.today().isoformat()
    logger.info(f"Generating daily summary report for {today}...")

    try:
        logs = db.get_logs_for_date(today)
        total = len(logs)
        sent = sum(1 for l in logs if l["status"] == "sent")
        failed = total - sent
        success_rate = (sent / total * 100) if total > 0 else 0

        logger.info(f"Fetched {total} log entries for {today}. Sent: {sent}, Failed: {failed}")

        body = f"""
===================================
MindFuel Daily Delivery Report
===================================

Date: {today}

Summary:
    • Total Emails Attempted : {total}
    • Successfully Delivered  : {sent}
    • Failed Deliveries       : {failed}
    • Success Rate            : {success_rate:.2f}%

Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'Action Recommended: Please review the failed logs in the database for troubleshooting.'
 if failed > 0 else 'All emails were delivered successfully today.'}

You can review detailed error traces in the application log file or the email_logs table.

Kind Regards,  
MindFuel Automation System  
"""

        msg = EmailMessage()
        msg["Subject"] = f"MindFuel Daily Summary Report — {today}"
        msg["From"] = FROM_EMAIL
        msg["To"] = ADMIN_EMAIL
        msg.set_content(body)

        logger.info(f"Attempting to send summary email to admin: {ADMIN_EMAIL}")

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
            smtp.ehlo()
            if SMTP_PORT == 587:
                smtp.starttls()
                smtp.ehlo()

            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)

        logger.info(f"Summary email successfully sent to admin {ADMIN_EMAIL}")
        return True

    except Exception as e:
        logger.exception(f"Failed to send summary email to admin {ADMIN_EMAIL}: {e}")
        return False

