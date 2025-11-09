"""Process DB rows into Jira requests and update tracking state."""
from typing import Dict, Any, Tuple, Optional
from logging_config import setup_logger
from transformer import build_form_answers, to_date_obj
from jira_helpers import create_request_on_jira
from config import SITE_DOMAIN, SERVICE_DESK_ID, REQUEST_TYPE_ID, DB_TO_QID
from mappers import map_handsets_field_dynamic
logger = setup_logger(__name__)

def process_row(
    row: Dict[str, Any],
    tracking: Dict[str, Any],
    questions: Dict[str, Any],
    choice_map: Dict[str, Dict[str, str]]
) -> Tuple[Dict[str, Any], bool, Optional[str], Optional[str]]:
    """
    Process a single database row and attempt to submit a Jira ServiceDesk request.

    Main responsibilities of this function:
    - Validate the DB row (must have email)
    - Prevent creating duplicate Jira issues for the same email (using tracking state)
    - Build summary + description text for the Jira ticket
    - Convert DB values to Jira form-answer structure using `build_form_answers`
    - Handle special logic for handsets multi-select field
    - Call Jira API to create the request
    - Update tracking state with created issues + return processing outcome

    Returns a tuple:
        (updated_tracking_state, processed_flag, created_date_iso, email)
    """
    
    # Extract email from DB row. If missing, we cannot process this record.
    email = row.get('emailaddress') or row.get('email') or row.get('Email')
    if not email:
        logger.warning('Skipping row without email: %s', row)
        return tracking, False, None, None

    # Skip this row if this email already produced a Jira request previously.
    if email in tracking.get('email_to_issue', {}):
        logger.info('Email %s already has JIRA issue; skipping row', email)
        return tracking, False, None, email

    # Build Jira summary and description body
    # Summary used as Jira ticket title
    summary = f"Phone equipment request - {row.get('newusername') or email}"

    # Description shows useful fields
    description_parts = []
    for col in ['newusername', 'phonenumber', 'departmentname', 'job', 'costcenter', 'comments']:
        if row.get(col):
            description_parts.append(f"{col}: {row.get(col)}")

    description = "\n".join(description_parts) or "Phone equipment request"

    # Convert DB row to form answers
    # If mapping fails (invalid values) the row skipped
    form_answers = build_form_answers(row, questions, choice_map, tracking)
    if form_answers is None:
        logger.info('Row %s invalid/flagged → SKIPPING Jira', email)
        created_iso = to_date_obj(row.get('createdat')).isoformat() if to_date_obj(row.get('createdat')) else None
        return tracking, False, created_iso, email

    # Special case handling for multi-select column "handsetsandheadsets"
    # DB stores them semicolon separated -> convert dynamically to form choices.
    handsets_col = 'handsetsandheadsets'
    handsets_qid = DB_TO_QID.get(handsets_col) # mapping DB column to form question ID
    if handsets_qid:
        raw_value = row.get(handsets_col)
        if raw_value:
            mapped_choice_ids = map_handsets_field_dynamic(raw_value, questions)
            if mapped_choice_ids:
                form_answers[str(handsets_qid)] = {'choices': mapped_choice_ids}

    # SEND request to Jira
    try:
        resp = create_request_on_jira(
            SITE_DOMAIN, SERVICE_DESK_ID, REQUEST_TYPE_ID, summary, description, form_answers
        )
        # Extract Jira issue reference key in the safest way possible
        issue_key = (
            resp.get('issueKey') or
            (resp.get('request') and resp['request'].get('issueKey')) or
            resp.get('key') or
            resp.get('requestNumber') or
            str(resp)[:200]
        )
        logger.info('Created Jira request %s for %s', issue_key, email)
    except Exception:
        logger.exception("Failed creating Jira issue for email: %s", email)
        created_iso = to_date_obj(row.get('createdat')).isoformat() if to_date_obj(row.get('createdat')) else None
        return tracking, False, created_iso, email

    # Store successful result back into tracking state
    tracking.setdefault('email_to_issue', {})[email] = issue_key

    # return created date as iso yyyy-mm-dd
    rd = to_date_obj(row.get('createdat'))
    created_iso = rd.isoformat() if rd else None

    return tracking, True, created_iso, email

