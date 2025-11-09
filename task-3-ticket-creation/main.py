
from logging_config import setup_logger
from state_manager import read_tracking, write_tracking
from db_helpers import fetch_rows_on_or_after
from tracking_manager import filter_rows_for_processing, finalize_tracking_after_run
from form_mapping import extract_questions_from_form, build_choice_label_to_id_map
from jira_helpers import fetch_form_definition_cloud
from processor import process_row
from datetime import date
from config import CLOUD_ID, SERVICE_DESK_ID, REQUEST_TYPE_ID, TRACKING_FILE
logger = setup_logger(__name__)

def main() -> None:
    """
    Main entry point of the Jira Form Automation pipeline.

    What this function does:
    - Load the tracking state file (used for incremental processing)
    - Fetch Jira form structure (Form JSON) so we can dynamically map choices/fields
    - Build helper lookup maps for fast conversion of DB values → Jira choice IDs
    - Fetch rows from Postgres that are >= last_run_date (incremental ingestion)
    - Filter rows to remove duplicates / prevent reprocessing
    - Process each unprocessed DB row → submit Jira request + update tracking
    - Update the tracking file at the end so next run only processes NEW data

    This function is the orchestrator that binds every other helper function together.

    Run as:
    python main.py
    """
    # Load persisted state (last processed run date, flagged requests, processed emails)
    tracking = read_tracking(TRACKING_FILE)
    logger.info('Starting run. last_run_date=%s', tracking.get('last_run_date'))

    # ------------------ Fetch form definition and create lookup maps -------------------
    # Fetch the form JSON from Jira Cloud API
    form_json = fetch_form_definition_cloud(CLOUD_ID, SERVICE_DESK_ID, REQUEST_TYPE_ID)

    # Extract questions dict since Jira returns a huge nested JSON structure
    questions = extract_questions_from_form(form_json)

    # Build normalized label → choice_id maps for each selectable Jira field
    choice_map = build_choice_label_to_id_map(questions)

    # ------------------ Load candidate DB rows ----------------------------------------
    # Fetch rows from DB only from the last run forward (incremental ETL logic)
    rows = fetch_rows_on_or_after(tracking.get('last_run_date'))

    # Further filtering: remove duplicates per email & remove already submitted ones
    rows_to_process = filter_rows_for_processing(rows, tracking)
    if not rows_to_process:
        logger.info('No rows to process. Exiting.')
        return

    # ------------------ Process each row ----------------------------------------------
    # Track emails that were processed today only (so tracking can be updated correctly)
    emails_processed_today = set()

    for row in rows_to_process:
        try:
            # This does the following:
            # - validate fields
            # - build answers
            # - create Jira request
            # - update tracking
            tracking, processed, row_date_str, email = process_row(row, tracking, questions, choice_map)

            # Persist tracking immediately so if script crashes we don't lose progress
            write_tracking(tracking, TRACKING_FILE)

            # Track emails processed TODAY to allow finalize_tracking to update date correctly
            if processed and row_date_str:
                if row_date_str == date.today().isoformat() and email:
                    emails_processed_today.add(email)

        except Exception:
            logger.exception('Unexpected error processing row: %s', row)

    # ------------------ Finalize run ---------------------------------------------------
    # Update last run date based on if any row for today was processed
    tracking = finalize_tracking_after_run(tracking, emails_processed_today)

    # Persist final tracking state back to json file
    write_tracking(tracking, TRACKING_FILE)

    logger.info('Run complete.')


if __name__ == '__main__':
    main()