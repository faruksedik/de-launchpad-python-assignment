"""Database helpers using psycopg2 to fetch rows incrementally."""
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
import psycopg2
from logging_config import setup_logger
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, PHONEREQUEST_TABLE, CREATEDAT_COL

logger = setup_logger(__name__)

@contextmanager
def get_conn():
    """
    Yield a psycopg2 connection and ensure it is closed.

    Raises:
        psycopg2.Error: If DB connection fails
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.debug("DB connection established successfully.")
        yield conn
    except Exception as e:
        logger.exception("Database connection error: %s", str(e))
        raise
    finally:
        try:
            conn.close()
            logger.debug("DB connection closed.")
        except Exception:
            pass


def fetch_rows_on_or_after(start_date: Optional[str]) -> List[Dict[str, Any]]:
    """
    Fetch rows where createdat >= start_date (or all rows if None)

    Args:
        start_date (str|None): 'YYYY-MM-DD' or None

    Returns:
        List[Dict[str, Any]]
    """
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if start_date:
                    sql = f"SELECT * FROM {PHONEREQUEST_TABLE} WHERE {CREATEDAT_COL} >= %s ORDER BY {CREATEDAT_COL} ASC"
                    cur.execute(sql, (start_date,))
                else:
                    sql = f"SELECT * FROM {PHONEREQUEST_TABLE} ORDER BY {CREATEDAT_COL} ASC"
                    cur.execute(sql)

                rows = cur.fetchall()
                logger.info("Fetched %d rows from DB", len(rows))
                return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("Error reading rows from DB: %s", str(e))
        return []

