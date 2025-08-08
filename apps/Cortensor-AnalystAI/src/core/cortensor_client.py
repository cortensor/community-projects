import logging
import requests
from src.config import CORTENSOR_API_URL, CORTENSOR_API_KEY, CORTENSOR_SESSION_ID

logger = logging.getLogger(__name__)

def get_ai_analysis(request_id: str, prompt: str) -> str | None:
    """Sends a prompt to the Cortensor API with adjusted temperature."""
    if not CORTENSOR_SESSION_ID:
        logger.error(f"CORTENSOR_SESSION_ID is not configured. Aborting request {request_id}.")
        return None
    if not CORTENSOR_API_URL:
        logger.error(f"CORTENSOR_API_URL is not configured. Aborting request {request_id}.")
        return None
    if not CORTENSOR_API_KEY:
        logger.error(f"CORTENSOR_API_KEY is not configured. Aborting request {request_id}.")
        return None

    headers = {
        "Authorization": f"Bearer {CORTENSOR_API_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": request_id
    }
    
    payload = {
        "session_id": int(CORTENSOR_SESSION_ID),
        "prompt": prompt,
        "prompt_type": 1,
        "temperature": 0.3,
        "stream": False,
        "timeout": 300,
        "max_tokens": 5024
    }

    try:
        logger.info(f"Sending request for ID {request_id} to Cortensor API with temperature=0.3.")
        response = requests.post(CORTENSOR_API_URL, headers=headers, json=payload, timeout=320)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        response_data = response.json()
        logger.debug(f"Cortensor API raw response for {request_id}: {response_data}")

        # Check if 'choices' key exists and is a list
        if 'choices' in response_data and isinstance(response_data['choices'], list):
            # Check if the list is not empty and has a dictionary at index 0
            if response_data['choices'] and isinstance(response_data['choices'][0], dict):
                answer = response_data['choices'][0].get('text')
                if answer:
                    logger.info(f"Cortensor API response for {request_id} successfully parsed.")
                    return answer.strip()
                else:
                    logger.warning(f"Cortensor API response for {request_id} has 'choices' but 'text' key is missing or empty in the first choice.")
            else:
                logger.warning(f"Cortensor API response for {request_id} has 'choices' but the first element is not a dictionary or is empty.")
        else:
            logger.warning(f"Cortensor API response for {request_id} is missing 'choices' key or it's not a list. Full response: {response_data}")

        return None # Return None if parsing failed

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred in cortensor_client for {request_id}: {http_err}. Response: {response.text}", exc_info=True)
        return None
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error occurred in cortensor_client for {request_id}: {conn_err}", exc_info=True)
        return None
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error occurred in cortensor_client for {request_id}: {timeout_err}", exc_info=True)
        return None
    except requests.exceptions.RequestException as req_err:
        logger.error(f"A general request error occurred in cortensor_client for {request_id}: {req_err}", exc_info=True)
        return None
    except Exception as e: # Catch any other unexpected errors during JSON processing
        logger.error(f"An unexpected error occurred in cortensor_client for {request_id} during JSON processing: {e}. Raw response data: {response_data}", exc_info=True)
        return None