# quotes.py
import requests
import random
from logger_config import get_logger
from config import ZEN_QUOTES_URL

logger = get_logger("quotes")

def fetch_quotes(timeout=10, limit=20):
    """
    Fetch multiple motivational quotes from the ZenQuotes API with robust error handling.

    This function sends a GET request to the ZenQuotes API, parses the JSON response,
    and returns a validated list of quote dictionaries. Handles all common network issues
    (timeouts, DNS errors, redirects, malformed responses).

    Args:
        timeout (int, optional): Maximum time (in seconds) to wait for the API response.
            Defaults to 10.
        limit (int, optional): The number of quotes to return from the API result.
            Defaults to 20.

    Returns:
        list[dict]: A list of quote dictionaries in the format:
            [
                {"quote": "Life is what happens...", "author": "John Lennon"},
                {"quote": "Do or do not...", "author": "Yoda"},
                ...
            ]

    Raises:
        ValueError: If the API response cannot be parsed as JSON or contains no valid quotes.
        Exception: If all retry attempts fail or a fatal HTTP error occurs.

    Logging:
        - INFO: When starting and finishing the fetch process.
        - DEBUG: When making API requests and parsing JSON.
        - WARNING: When skipping malformed entries.
        - ERROR: When network, timeout, or data errors occur.
    """
    logger.info(f"Starting fetch from ZenQuotes API (limit={limit}, timeout={timeout}s)...")

    try:
        # Perform the API call
        resp = requests.get(ZEN_QUOTES_URL, timeout=timeout)
        resp.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
        logger.debug(f"API request sent to {ZEN_QUOTES_URL}. Status code: {resp.status_code}")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout after {timeout}s when fetching quotes from ZenQuotes API.", exc_info=True)
        raise Exception(f"Request timed out after {timeout} seconds.")

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error while reaching ZenQuotes API: {e}", exc_info=True)
        raise Exception("Unable to connect to ZenQuotes API. Check your internet connection or API status.")

    except requests.exceptions.TooManyRedirects as e:
        logger.error(f"Too many redirects when contacting ZenQuotes API: {e}", exc_info=True)
        raise Exception("ZenQuotes API caused too many redirects.")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error from ZenQuotes API: {e}", exc_info=True)
        raise Exception(f"ZenQuotes API returned bad HTTP status: {resp.status_code}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Unexpected network error fetching quotes: {e}", exc_info=True)
        raise Exception("Unexpected network issue occurred while contacting ZenQuotes API.")

    # Parse JSON safely
    try:
        data = resp.json()
        logger.debug("ZenQuotes API response successfully parsed as JSON.")
    except ValueError as e:
        logger.error(f"Malformed JSON response from ZenQuotes: {e}", exc_info=True)
        raise ValueError("Malformed JSON received from ZenQuotes API.")

    # Validate quote structure
    quotes_list = []
    for item in data[:limit]:
        if "q" in item and "a" in item:
            quotes_list.append({
                "quote": item["q"].strip(),
                "author": item.get("a", "Unknown").strip()
            })
        else:
            logger.warning(f"Skipping malformed quote entry: {item}")

    if not quotes_list:
        logger.error("No valid quotes returned from ZenQuotes API.")
        raise ValueError("ZenQuotes API returned no valid quotes.")

    logger.info(f"Successfully fetched {len(quotes_list)} quotes from ZenQuotes API.")
    return quotes_list




def get_random_quote(quotes_list):
    """
    Select and return a random quote from a list of quotes.

    This function takes a list of quote dictionaries (as returned by `fetch_quotes`)
    and returns one random quote. It ensures the list is not empty before selection.

    Args:
        quotes_list (list[dict]): A list of quote dictionaries, each containing:
            - 'quote' (str): The quote text.
            - 'author' (str): The author of the quote.

    Returns:
        dict: A single randomly selected quote in the format:
            {"quote": "Be yourself; everyone else is already taken.", "author": "Oscar Wilde"}

    Raises:
        ValueError: If the input list is empty.

    Logging:
        - DEBUG: When starting the random selection process.
        - INFO: When a quote is successfully selected.
        - ERROR: When attempting to select from an empty list.
    """
    logger.debug("Selecting a random quote from the fetched quotes list.")
    if not quotes_list:
        logger.error("Attempted to pick a random quote from an empty list.")
        raise ValueError("Empty quotes list provided to get_random_quote")
    
    quote = random.choice(quotes_list)
    logger.info(f"Selected random quote by '{quote['author']}': \"{quote['quote']}\"")
    return quote
