"""Transform DB rows into Jira form 'answers' payload and validate timeframe.

Contains helpers to convert date-like values and to build the 'answers' dict
for the Jira create request API. The function uses the dynamic questions map
and the choice_map (label->id) produced from the form JSON.
"""
from typing import Any, Dict, Optional, List
from datetime import datetime, date
from logging_config import setup_logger
from config import DB_TO_QID
logger = setup_logger(__name__)

def to_date_obj(value: Optional[Any]) -> Optional[date]:
    """Convert a DB value to datetime.date.

    Args:
        value: value from DB (date, datetime, or ISO string)

    Returns:
        Optional[date]: date or None if conversion fails
    """
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date()
        except Exception:
            return None
    return None


def build_form_answers(
    row: Dict[str, Any],
    questions: Dict[str, Any],
    choice_map: Dict[str, Dict[str, str]],
    tracking: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Convert a single DB row into the required Jira form `answers` payload.

    What this function does:
    - Validate and map the timeframe column to a Jira choice id.
    - Apply business rules for temporary vs permanent requests.
    - Convert DB fields into Jira "answers" based on question type definitions.
    - Record flagged rows back into tracking if validation fails.

    Validation rules:
    - timeframe must map to a known choice id
    - if timeframe == temporary -> dateneededby and approximateendingdate must be present and approx > needed
    - if timeframe == permanent -> approximateendingdate is ignored

    Args:
        row: DB row dict
        questions: form questions mapping
        choice_map: mapping qid -> normalized_label -> choice_id
        tracking: tracking state dict (may be updated with flagged requests)

    Returns:
        Optional[Dict[str, Any]]: answers dict or None if validation fails
    """

    answers: Dict[str, Any] = {}
    email = row.get('emailaddress') or row.get('email') or row.get('Email')

    # --- PROCESS TIMEFRAME ---
    # convert timeframe to normalized key and map into Jira choice id
    timeframe_qid = DB_TO_QID['timeframe']
    timeframe_raw = str(row.get('timeframe') or '').strip()
    timeframe_norm = ''.join(ch for ch in timeframe_raw.lower() if ch.isalnum())
    timeframe_choice_map = choice_map.get(timeframe_qid, {})
    timeframe_choice_id = timeframe_choice_map.get(timeframe_norm)

    if not timeframe_choice_id:
        # invalid timeframe → mark as flagged → skip processing
        logger.warning("Could not map timeframe '%s' for %s", timeframe_raw, email)
        tracking.setdefault('flagged_requests', {})[email] = f"Invalid timeframe: {timeframe_raw}"
        return None

    # store timeframe field in Jira answer format
    answers[timeframe_qid] = {'choices': [timeframe_choice_id]}

    # --- DATE VALIDATION ---
    # temporary requests must have required date fields + approx_end > date_needed
    date_needed = to_date_obj(row.get('dateneededby'))
    approx_end = to_date_obj(row.get('approximateendingdate'))

    if timeframe_norm == 'temporary':
        # if missing dates → cannot process
        if not date_needed or not approx_end:
            tracking.setdefault('flagged_requests', {})[email] = 'Missing date(s) for temporary request'
            logger.warning('Temporary request missing dates for %s', email)
            return None

        # approx ending date must be greater than needed date
        if not (approx_end > date_needed):
            tracking.setdefault('flagged_requests', {})[email] = 'approximateendingdate <= dateneededby'
            logger.warning('Temporary request date validation failed for %s', email)
            return None

    # permanent requests ignore approx ending date
    elif timeframe_norm == 'permanent':
        approx_end = None

    # --- MAP REMAINING FIELDS ---
    # For every DB column mapped to a question ID → convert to Jira compatible field type
    # (multi-select handset handled separately later)
    for db_col, qid in DB_TO_QID.items():
        if db_col in ('timeframe', 'handsetsandheadsets'):
            continue

        value = row.get(db_col)
        if value is None:
            continue

        # determine question type: text/date/choice etc
        qdef = questions.get(qid, {})
        qtype = qdef.get('type', '')

        # TEXT
        if qtype in ('ts', 'te', 'pg', 'text'):
            answers[qid] = {'text': str(value)}

        # DATE
        elif qtype == 'da':
            d = to_date_obj(value)
            answers[qid] = {'date': d.isoformat() if d else str(value)}

        # CHOICE / MULTI CHOICE
        elif qtype in ('cs', 'cm'):
            # convert DB values to list of labels
            if isinstance(value, list):
                labels = [str(x).strip() for x in value if x]
            else:
                labels = [s.strip() for s in str(value).split(',') if s.strip()]

            # find matching choice ids via normalized comparison
            choice_ids: List[str] = []
            q_choice_map = choice_map.get(qid, {})

            for label in labels:
                norm_label = ''.join(ch for ch in label.lower() if ch.isalnum())
                cid = q_choice_map.get(norm_label)

                if cid:
                    choice_ids.append(cid)
                else:
                    # fuzzy match fallback
                    for k_norm, k_id in q_choice_map.items():
                        if norm_label in k_norm or k_norm in norm_label:
                            choice_ids.append(k_id)
                            break

            # only store if we found a valid match
            if choice_ids:
                answers[qid] = {'choices': choice_ids}

        # DEFAULT fallback, treat as text
        else:
            answers[qid] = {'text': str(value)}

    return answers

