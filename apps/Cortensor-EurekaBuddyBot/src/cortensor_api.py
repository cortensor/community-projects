import logging
from typing import Dict, Tuple, Optional, List
import requests

from .config import (
    CORTENSOR_API_URL,
    CORTENSOR_API_KEY,
    CORTENSOR_SESSION_ID,
    CORTENSOR_TLS_INSECURE,
    CORTENSOR_HOST_HEADER,
    CORTENSOR_PROMPT_TYPE,
)

logger = logging.getLogger(__name__)

def build_headers() -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {CORTENSOR_API_KEY}",
        "Content-Type": "application/json",
    }
    if CORTENSOR_HOST_HEADER:
        headers["Host"] = CORTENSOR_HOST_HEADER
    return headers

def build_payload(prompt: str, provider: Optional[str], model: Optional[str]) -> Dict:
    payload = {
        "session_id": CORTENSOR_SESSION_ID,
        "prompt": prompt,
        "stream": False,
        "timeout": 180,
    }
    # Force RAW prompt type by default; allow override via env if explicitly set to other numeric
    try:
        pt = int(CORTENSOR_PROMPT_TYPE)
    except (TypeError, ValueError):
        pt = 1
    payload["prompt_type"] = pt if pt else 1
    if provider:
        payload["provider"] = provider
    if model:
        payload["model"] = model
    return payload

def _endpoint_candidates(base_url: str, session_id: str) -> List[Tuple[str, Dict[str, str]]]:
    cands: List[Tuple[str, Dict[str, str]]] = []
    if base_url.endswith("/completions"):
        cands.append((base_url, {"use_session_in_path": "0"}))
        cands.append((f"{base_url.rstrip('/')}/{session_id}", {"use_session_in_path": "1"}))
    elif base_url.endswith("/api/v1"):
        cands.append((f"{base_url}/completions", {"use_session_in_path": "0"}))
        cands.append((f"{base_url}/completions/{session_id}", {"use_session_in_path": "1"}))
    else:
        cands.append((f"{base_url.rstrip('/')}/api/v1/completions", {"use_session_in_path": "0"}))
        cands.append((f"{base_url.rstrip('/')}/api/v1/completions/{session_id}", {"use_session_in_path": "1"}))
    return cands

def request_completion(prompt: str, provider: Optional[str], model: Optional[str]) -> Dict:
    headers = build_headers()
    payload = build_payload(prompt, provider, model)

    base_url = CORTENSOR_API_URL or ""
    logger.info(f"Preparing request to {base_url} with provider/model: {provider}/{model}")

    # Try with given scheme first, then flip https<->http on SSL errors
    schemes = []
    if base_url.startswith("http://"):
        schemes = [base_url, base_url.replace("http://", "https://", 1)]
    elif base_url.startswith("https://"):
        schemes = [base_url, base_url.replace("https://", "http://", 1)]
    else:
        schemes = [f"http://{base_url}", f"https://{base_url}"]

    last_exc = None
    for scheme_url in schemes:
        candidates = _endpoint_candidates(scheme_url, str(CORTENSOR_SESSION_ID))
        for url, meta in candidates:
            try:
                logger.info(f"POST {url}")
                body = payload if meta.get("use_session_in_path") == "0" else {k: v for k, v in payload.items() if k != "session_id"}
                response = requests.post(
                    url,
                    headers=headers,
                    json=body,
                    timeout=320,
                    verify=not CORTENSOR_TLS_INSECURE,
                )
                if response.status_code == 404:
                    logger.warning(f"Endpoint 404 at {url}, trying next candidate if any...")
                    continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.SSLError as ssl_err:
                last_exc = ssl_err
                logger.warning(f"SSL error on {url}: {ssl_err}. Will try alternate scheme if available.")
                break  # break inner loop to flip scheme
            except requests.exceptions.HTTPError as http_err:
                last_exc = http_err
                if getattr(http_err.response, 'status_code', None) != 404:
                    raise
                logger.warning(f"HTTP 404 at {url}, will try next candidate if available.")
                continue
            except requests.exceptions.RequestException as req_err:
                last_exc = req_err
                logger.warning(f"Request error at {url}: {req_err}. Trying next candidate.")
                continue
        # continue to next scheme on SSL error
        continue

    if last_exc:
        raise last_exc
    raise requests.exceptions.HTTPError("All endpoint candidates failed.")
