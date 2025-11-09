"""Helpers to extract questions and build choice label->id maps from form JSON."""
from typing import Dict, Any
from logging_config import setup_logger
logger = setup_logger(__name__)

def extract_questions_from_form(form_json: Dict[str, Any]) -> Dict[str, Any]:
    """Extract 'questions' dict from form JSON.

    Args:
        form_json: raw form JSON from Jira

    Returns:
        Dict[str, Any]: mapping of qid -> question object
    """
    return form_json.get('design', {}).get('questions', {}) or {}


def build_choice_label_to_id_map(questions: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Build mapping of qid -> normalized_label -> choice_id for choice questions.

    This map is essential for transforming a text value received from the database
    (which corresponds to a user-visible choice label) into the internal ID that
    the Jira API requires for single-select or multi-select fields.

    Args:
        questions: The dictionary of question objects, typically retrieved directly 
                   from the 'design' section of the Jira form JSON definition.

    Returns:
        Dict[str, Dict[str, str]]: A nested dictionary mapping:
                                  { Question ID: { Normalized Label: Choice ID } }
    """
    
    # Define an inner helper function to normalize text.
    # This ensures lookup keys are consistent, ignoring case and punctuation.
    def _normalize(s: str) -> str:
        return ''.join(ch for ch in s.lower() if ch.isalnum()) if s else ''
        
    m = {} # Initialize the main mapping dictionary.
    
    # Iterate through every question in the form definition.
    for qid, qobj in questions.items():
        choices = qobj.get('choices') or []
        
        # Skip questions that are not choice-based (e.g., text, date fields).
        if not choices:
            continue
            
        inner = {} # Initialize the map for the current Question ID (QID).
        
        # Process each choice to create the normalized label -> ID mapping.
        for ch in choices:
            lab = ch.get('label')
            cid = ch.get('id')
            
            # Map the normalized human-readable label to the internal Jira ID.
            if lab and cid is not None:
                inner[_normalize(lab)] = str(cid)
                
        # Only include the QID in the main map if it successfully processed choices.
        if inner:
            m[qid] = inner
            
    return m