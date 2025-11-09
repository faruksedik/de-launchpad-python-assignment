"""Filtering logic for incremental processing and finalizing tracking state."""
from typing import List, Dict, Any, Set
from datetime import date
from transformer import to_date_obj
from logging_config import setup_logger

logger = setup_logger(__name__)

def filter_rows_for_processing(rows: List[Dict[str, Any]], tracking: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Determine which database rows should be processed based on incremental rules.

    This function prevents processing same records multiple times by:
    1. Processing all rows if there is no past run recorded.
    2. Processing only rows whose created date is newer than the last run date.
    3. Processing rows from the same day ONLY IF their email has not been processed before.
    4. Ignoring older rows completely.

    Args:
        rows: List of database row records. Each row must contain 'createdat' and email column.
        tracking: Dict holding values for last_run_date and list of processed emails for that date.

    Returns:
        List of rows that need to be processed in this run.
    """

    # load last successful run date; None means this is first ever run.
    last_run_date = tracking.get('last_run_date')

    # convert stored processed emails to set for fast lookup.
    processed_emails_same_date = set(tracking.get('processed_emails_same_date', []))

    # collect rows allowed for processing
    to_process = []

    for r in rows:
        # convert DB raw string date into python date object
        rd = to_date_obj(r.get('createdat'))
        if rd is None:
            # if invalid date, skip silently
            logger.warning("Skipping row with invalid createdat: %s", r)
            continue

        row_date_str = rd.isoformat()  # convert back to YYYY-MM-DD

        # read email field reliably with fallback column names
        email = r.get('emailaddress') or r.get('email') or r.get('Email')

        # First time ever running the script → process EVERYTHING.
        if last_run_date is None:
            to_process.append(r)
            continue

        # If this row is from a NEWER date → always process it.
        if row_date_str > last_run_date:
            to_process.append(r)

        # If this row is same date as last run → process only if email not processed earlier that same day.
        elif row_date_str == last_run_date:
            if not email:
                logger.warning("Skipping same-day row without email: %s", r)
                continue
            if email not in processed_emails_same_date:
                to_process.append(r)
            else:
                logger.info("Skipping already processed same-day email: %s", email)

        # If this row date is older than our last run date → ignore it.
        else:
            logger.debug("Skipping older row: %s", r)

    return to_process


def finalize_tracking_after_run(tracking: Dict[str, Any], emails_processed_today: Set[str]) -> Dict[str, Any]:
    """
    Update tracking state after a successful pipeline run.

    This function writes the current date as the new last_run_date
    and stores all emails processed today. This allows next run to skip
    these emails if they reappear on the same date.

    Args:
        tracking: existing tracking state dict
        emails_processed_today: set of unique emails processed in this current run

    Returns:
        Updated tracking dict which should be persisted to disk afterwards.
    """

    # Get today's date string (YYYY-MM-DD)
    today_str = date.today().isoformat()

    # Mark today's date as the last successful processed date
    tracking['last_run_date'] = today_str

    # Store processed emails to avoid duplicate Jira creation on same date next run
    tracking['processed_emails_same_date'] = sorted(emails_processed_today)

    logger.info(
        "Finalized tracking: last_run_date=%s processed_emails_same_date=%s",
        tracking['last_run_date'], tracking['processed_emails_same_date']
    )

    return tracking

