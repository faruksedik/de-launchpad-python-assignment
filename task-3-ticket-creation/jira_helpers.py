"""Helpers for interacting with Jira Forms and Service Desk APIs."""
from typing import Dict, Any
import requests
from requests.auth import HTTPBasicAuth
from logging_config import setup_logger
from config import JIRA_EMAIL, JIRA_API_TOKEN, SITE_DOMAIN
logger = setup_logger(__name__)

def jira_auth() -> HTTPBasicAuth:
    """Return HTTPBasicAuth for Jira API calls.

    Returns:
        HTTPBasicAuth: auth object for requests
    """
    return HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

def fetch_form_definition_cloud(
    cloud_id: str,
    service_desk_id: str,
    request_type_id: str,
    auth=None
) -> Dict[str, Any]:
    """
    Fetch the form JSON for a Jira Cloud form request type.

    Args:
        cloud_id (str): Atlassian Cloud ID (tenant ID)
        service_desk_id (str): Jira Service Desk ID
        request_type_id (str): Request Type ID
        auth: Optional authentication object for requests. If None, will use jira_auth().

    Returns:
        Dict[str, Any]: Parsed form JSON dictionary.
    """

    # --- Parameter validation ---
    if not cloud_id or not service_desk_id or not request_type_id:
        raise ValueError("cloud_id, service_desk_id, and request_type_id must not be empty")

    if auth is None:
        auth = jira_auth()

    # --- Build URL ---
    url = (
        f"https://api.atlassian.com/jira/forms/cloud/"
        f"{cloud_id}/servicedesk/{service_desk_id}/requesttype/{request_type_id}/form"
    )

    headers = {"Accept": "application/json"}
    logger.info(f"[Form Fetch] Fetching form definition -> Cloud={cloud_id}, Desk={service_desk_id}, Type={request_type_id}")

    # --- attempt with retry ---
    for attempt in range(1, 4):  # retry max 3 times
        try:
            resp = requests.get(url, auth=auth, headers=headers, timeout=30)

            if resp.status_code in (200, 201):
                try:
                    return resp.json()
                except ValueError as e:
                    logger.error("API returned non JSON response")
                    raise ValueError("Response from Jira was not JSON") from e

            # not OK -> log and retry
            logger.warning(f"Attempt {attempt}/3: Failed Jira form fetch: {resp.status_code} -> {resp.text}")

        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt}/3: Network/API error occurred -> {e}")

    # after retry exhausted
    logger.error(f"Failed to fetch form definition after 3 attempts: {url}")
    raise RuntimeError("Unable to fetch Jira form JSON after retries")


def create_request_on_jira(site_domain: str, service_desk_id: str, request_type_id: str, summary: str, description: str, form_answers: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Jira Service Desk customer request using the form answers.

    Args:
        site_domain: your Jira site domain
        service_desk_id: service desk id
        request_type_id: request type id
        summary: request summary
        description: request description
        form_answers: answers dict for the form

    Returns:
        Dict[str, Any]: parsed response JSON
    """
    url = f"https://{site_domain}/rest/servicedeskapi/request"
    payload = {
        "form": {"answers": form_answers},
        "isAdfRequest": False,
        "requestFieldValues": {"summary": summary, "description": description},
        "requestTypeId": str(request_type_id),
        "serviceDeskId": str(service_desk_id)
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    logger.info("Creating Jira request: %s", summary)
    resp = requests.post(url, auth=jira_auth(), headers=headers, json=payload, timeout=30)
    if resp.status_code not in (200, 201):
        logger.error("Failed to create Jira request: %s - %s", resp.status_code, resp.text)
        resp.raise_for_status()
    return resp.json()
