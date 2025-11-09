"""Read and write the JSON tracking file used for incremental loads."""
import json
from pathlib import Path
from typing import Dict, Any
from logging_config import setup_logger
from config import TRACKING_FILE

logger = setup_logger(__name__)

DEFAULT_STATE = {
    "last_run_date": None,
    "processed_emails_same_date": [],
    "email_to_issue": {},
    "flagged_requests": {}
}

def read_tracking(path: Path = TRACKING_FILE) -> Dict[str, Any]:
    """
    Read and load the tracking state from tracking.json.

    This file stores information about what requests/emails were processed
    previously so that the script can avoid duplicates, avoid re-processing
    same emails within the same day, and maintain reference mapping of
    email -> created Jira Issue Key.

    If the file does not exist yet OR if reading fails for any reason,
    the function will safely fall back to DEFAULT_STATE so application
    does not crash.
    """
    try:
        # If file does not exist, return default fresh state
        if not path.exists():
            logger.info("Tracking file not found; returning default state.")
            return dict(DEFAULT_STATE)

        # Load tracking file from disk
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        # Ensure all default keys exist (if older versions had missing keys)
        for k, v in DEFAULT_STATE.items():
            # If this key is missing, insert default for backward compatibility
            data.setdefault(
                k, dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v
            )

        return data

    except Exception:
        logger.exception("Failed to read tracking file. Returning safe default state.")
        return dict(DEFAULT_STATE)


def write_tracking(state: Dict[str, Any], path: Path = TRACKING_FILE) -> None:
    """
    Write/persist the tracking state to tracking.json.

    This is called AFTER each run of the pipeline,
    so that next run will continue from where it stopped
    and not re-process already processed requests/emails.
    """
    try:
        # dump into JSON file with pretty indentation
        with path.open("w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)

        logger.info("Tracking file successfully updated: %s", path)

    except Exception:
        logger.exception("Failed to write/save tracking file.")



