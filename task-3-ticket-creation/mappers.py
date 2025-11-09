"""Dynamic mapping helpers for Jira choice fields using form JSON.

This module contains helpers that map DB field values to Jira choice ids
using the live form JSON 'questions' block rather than hardcoded maps.
"""
from typing import List, Dict, Any

def _normalize_label(s: str) -> str:
    """Normalize a label string for matching (lower + alnum).

    Args:
        s: raw label string

    Returns:
        str: normalized label
    """
    if s is None:
        return ''
    return ''.join(ch for ch in s.lower() if ch.isalnum())

def map_handsets_field_dynamic(raw_value: str, questions: Dict[str, Any]) -> List[str]:
    """
    Convert/transform the handset values coming from the DB into Jira form Choice IDs.

    What this function does:
    - The DB stores handsets as text separated by semicolons e.g. "Cordless handset; Mobile phone"
    - Jira form requires the value to be submitted as choice IDs, not raw text labels.
    - This function reads the "handsets and headsets" question from the Jira form JSON (qid=159),
      builds a mapping of normalized_label: choice_id, then converts each DB handset label to
      the correct Jira choice id.
    - If a value cannot be mapped, we return "0" so we know it did not match any known option.

    Args:
        raw_value: semicolon separated text label coming from DB.
        questions: full questions dict from form JSON — we will extract choices inside here.

    Returns:
        A list of choice_ids (strings). Unknown labels always map to choice_id "0".
    """

    # If the database column is empty or None → return empty list
    if not raw_value:
        return []

    # Split the DB raw string into parts based on semicolon → and remove whitespace
    parts = [p.strip() for p in raw_value.split(';') if p.strip()]

    # Get the JIRA question for handsets and headsets (we confirmed qid=159 in our mapping)
    q = questions.get('159', {})

    # Extract the list of choices from question
    choices = q.get('choices') or []

    # Build normalized_label → choice_id mapping so matching becomes easier
    # We normalize labels to remove spaces and special chars before comparing
    label_map = {
        _normalize_label(ch.get('label')): str(ch.get('id'))
        for ch in choices if ch.get('label') is not None
    }

    # Use a list because Jira expects list of choice ids (and preserve order)
    seen = []

    # Convert each csv label from DB into normalized label → match id → store
    for p in parts:
        normalized = _normalize_label(p)                  # normalize DB label
        nid = label_map.get(normalized) or '0'            # if unknown → 0
        if nid not in seen:                               # no duplicates
            seen.append(nid)

    return seen

