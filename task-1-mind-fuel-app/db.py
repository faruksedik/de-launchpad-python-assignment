# db.py
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD
from logger_config import get_logger

logger = get_logger("db")

def get_conn():
    """Establish and return a PostgreSQL connection."""
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        logger.info(f"Successfully connected to database '{PG_DB}' on host '{PG_HOST}:{PG_PORT}'.")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database '{PG_DB}': {e}", exc_info=True)
        raise



@contextmanager
def conn_cursor(commit=False):
    """
    Context manager that safely yields a PostgreSQL database cursor 
    and ensures proper transaction handling.

    This function:
    - Opens a new database connection using `get_conn()`.
    - Yields a `RealDictCursor` that returns rows as dictionaries.
    - Commits the transaction automatically if `commit=True`.
    - Rolls back the transaction and logs the error if an exception occurs.
    - Closes both the cursor and the connection after execution.

    Args:
        commit (bool, optional): 
            Whether to commit the transaction after successful execution.
            Defaults to False.

    Yields:
        psycopg2.extras.RealDictCursor: 
            A cursor that returns query results as dictionaries.

    Example:
        >>> with conn_cursor(commit=True) as cur:
        ...     cur.execute("INSERT INTO users (email, name) VALUES (%s, %s)", ("test@example.com", "John"))
        ...     # Changes will be committed automatically when block exits

    Error Handling:
        - Rolls back any uncommitted transaction if an exception occurs.
        - Logs detailed error messages and traceback for debugging.
    """
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        yield cur
        if commit:
            conn.commit()
            logger.debug("Transaction committed successfully.")
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}", exc_info=True)
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()



def init_db():
    """Create tables: users and email_logs."""
    
    create_users = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(100),
        subscription_status VARCHAR(10) NOT NULL DEFAULT 'active', -- active or inactive
        email_frequency VARCHAR(10) NOT NULL DEFAULT 'daily', -- daily or weekly
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_email_received_at TIMESTAMP
    );
    """
    create_logs = """
    CREATE TABLE IF NOT EXISTS email_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        email VARCHAR(255),
        status VARCHAR(20), -- sent, failed
        error TEXT,
        attempt INT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with conn_cursor(commit=True) as cur:
            cur.execute(create_users)
            logger.info("Table 'users' created or already exists.")
            cur.execute(create_logs)
            logger.info("Table 'email_logs' created or already exists.")
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise


def add_user(email, name, subscription_status="active", email_frequency="daily"):
    """
    Add a new user to the database if they do not already exist.

    This function attempts to insert a new user record into the `users` table.
    If a user with the same email address already exists, the function does not
    perform any insertion (due to the `ON CONFLICT` clause) and returns None.
    Otherwise, it returns the ID of the newly added user.

    Args:
        email (str): The email address of the user. Must be unique.
        name (str): The full name of the user.
        subscription_status (str, optional): The user's subscription state.
            Defaults to "active". Possible values: "active" or "inactive".
        email_frequency (str, optional): The user's preferred email frequency.
            Defaults to "daily". Possible values: "daily" or "weekly".

    Returns:
        int | None: 
            - The ID of the newly created user if the insertion succeeds.
            - None if the user already exists (no new record inserted).

    Raises:
        Exception: If a database or SQL execution error occurs.

    Example:
        >>> add_user("jane.doe@example.com", "Jane Doe", email_frequency="weekly")
        7

        >>> add_user("jane.doe@example.com", "Jane Doe", email_frequency="weekly")
        None
    """
    sql = """
    INSERT INTO users (email, name, subscription_status, email_frequency)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (email) DO NOTHING
    RETURNING id;
    """
    try:
        with conn_cursor(commit=True) as cur:
            cur.execute(sql, (email, name, subscription_status, email_frequency))
            row = cur.fetchone()
            if row:
                logger.info(f"Added user '{email}' with ID {row['id']}.")
                return row['id']
            else:
                logger.info(f"ℹUser '{email}' already exists. No insertion made.")
                return None
    except Exception as e:
        logger.error(f"Error adding user '{email}': {e}", exc_info=True)
        raise



def get_eligible_subscribers(frequency):
    """
    Retrieve all active users eligible to receive an email based on their subscription frequency.

    A user is considered eligible if:
      - Their subscription status is 'active'.
      - Their `email_frequency` matches the given frequency.
      - They have either never received an email (`last_email_received_at IS NULL`) 
        or it's been at least the required interval since the last email:
          • "daily"  =  1 day interval
          • "weekly" =  7 days interval

    Args:
        frequency (str): Email frequency to filter users by. Must be "daily" or "weekly".

    Returns:
        list[dict]: A list of user records (as dictionaries) that meet the eligibility criteria.

    Raises:
        ValueError: If `frequency` is not "daily" or "weekly".
        Exception: If a database query or connection error occurs.

    Example:
        >>> get_eligible_subscribers("daily")
        [{'id': 1, 'email': 'user@example.com', 'name': 'User One', ...}]
    """
    if frequency == "daily":
        interval = "1 day"
    elif frequency == "weekly":
        interval = "7 days"
    else:
        raise ValueError("Invalid frequency: must be 'daily' or 'weekly'")

    sql = f"""
    SELECT * FROM users
    WHERE subscription_status='active'
    AND email_frequency=%s
    AND (last_email_received_at IS NULL OR last_email_received_at <= NOW() - INTERVAL '{interval}');
    """

    try:
        with conn_cursor() as cur:
            cur.execute(sql, (frequency,))
            rows = cur.fetchall()
            logger.info(f"Fetched {len(rows)} eligible subscribers for frequency '{frequency}'.")
            return rows
    except Exception as e:
        logger.error(f"Error fetching eligible subscribers for '{frequency}': {e}", exc_info=True)
        raise



def update_last_sent(user_id):
    """
    Update the 'last_email_received_at' timestamp for a specific user.

    This function is typically called after successfully sending an email
    to mark when the user last received a message.

    Args:
        user_id (int): The unique ID of the user whose record is being updated.

    Returns:
        None

    Raises:
        Exception: If a database update or connection error occurs.

    Example:
        >>> update_last_sent(12)
        Logs: "Updated last_email_received_at for user_id=12."
    """
    sql = "UPDATE users SET last_email_received_at = CURRENT_TIMESTAMP WHERE id = %s;"

    try:
        with conn_cursor(commit=True) as cur:
            cur.execute(sql, (user_id,))
            logger.info(f"Updated last_email_received_at for user_id={user_id}.")
    except Exception as e:
        logger.error(f"Failed to update last_email_received_at for user_id={user_id}. Error: {e}", exc_info=True)
        raise



def log_email(user_id, email, status, error=None, attempt=1):
    """
    Record the outcome of an email delivery attempt for a user.

    This function logs each attempt to send an email, storing relevant details
    such as the recipient, status (e.g., 'success' or 'failed'), any error message,
    and the attempt number.

    Args:
        user_id (int): The ID of the user the email was sent to.
        email (str): The recipient's email address.
        status (str): The result of the email attempt ("success" or "failed").
        error (str, optional): The error message if sending failed. Defaults to None.
        attempt (int, optional): The attempt number for this email send. Defaults to 1.

    Returns:
        int: The ID of the created email log record.

    Raises:
        Exception: If a database insertion or connection error occurs.

    Example:
        >>> log_email(3, "user@example.com", "success")
        15
    """

    sql = """
    INSERT INTO email_logs (user_id, email, status, error, attempt)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id;
    """
    try:
        with conn_cursor(commit=True) as cur:
            cur.execute(sql, (user_id, email, status, error, attempt))
            row = cur.fetchone()
            log_id = row['id']
            logger.info(f"Email log created for '{email}' (status={status}, attempt={attempt}). Log ID: {log_id}")
            return log_id
    except Exception as e:
        logger.error(f"Error logging email for '{email}': {e}", exc_info=True)
        raise


def get_logs_for_date(date_str):
    """
    Retrieve all email logs for a specific date.

    Args:
        date_str (str): The target date in 'YYYY-MM-DD' format.

    Returns:
        list[dict]: A list of email log entries sent on the specified date.

    Raises:
        Exception: If a database query or connection error occurs.

    Example:
        >>> get_logs_for_date("2025-10-27")
        [{'id': 2, 'email': 'user@example.com', 'status': 'success', ...}]
    """

    sql = """
    SELECT * FROM email_logs
    WHERE sent_at::date = %s::date;
    """
    try:
        with conn_cursor() as cur:
            cur.execute(sql, (date_str,))
            rows = cur.fetchall()
            logger.info(f"Retrieved {len(rows)} log(s) for date {date_str}.")
            return rows
    except Exception as e:
        logger.error(f"Error retrieving logs for date {date_str}: {e}", exc_info=True)
        raise
