import os
import re
import json
import logging
import requests
from typing import Dict, Any
from . import config

logger = logging.getLogger(__name__)


def _build_endpoint(base_url: str) -> str:
    """Build a safe completions endpoint per Cortensor Web2 API.

    Preference order (no mutation if full endpoint provided):
    - If URL already ends with '/api/v1/completions' or '/v1/chat/completions', return as-is.
    - If URL ends with '/api/v1' or '/v1', append '/completions'.
    - If URL has no path beyond host, append '/api/v1/completions'.
    """
    b = (base_url or '').strip().rstrip('/')
    if not b:
        return '/api/v1/completions'
    if b.endswith('/api/v1/completions') or b.endswith('/v1/chat/completions'):
        return b
    if b.endswith('/api/v1') or re.search(r'/v\d+$', b):
        return b + '/completions'
    # If it already ends with '/completions', keep as-is
    if b.endswith('/completions'):
        return b
    # Fallback to standard Web2 endpoint
    return b + '/api/v1/completions'


def _build_get_endpoint(base_url: str, name: str) -> str:
    b = (base_url or '').strip().rstrip('/')
    if not b:
        return f'/api/v1/{name}'
    if b.endswith('/api/v1/completions'):
        return b.rsplit('/api/v1/completions', 1)[0] + f'/api/v1/{name}'
    if b.endswith('/v1/chat/completions'):
        return b.rsplit('/v1/chat/completions', 1)[0] + f'/v1/{name}'
    if b.endswith('/api/v1') or re.search(r'/v\d+$', b):
        return b + f'/{name}'
    return b + f'/api/v1/{name}'


def router_info() -> Dict[str, Any]:
    url = _build_get_endpoint(config.CORTENSOR_API_URL, 'info')
    verify = not config.CORTENSOR_TLS_INSECURE
    headers = {'Authorization': f'Bearer {config.CORTENSOR_API_KEY}'}
    resp = requests.get(url, headers=headers, timeout=15, verify=verify)
    resp.raise_for_status()
    return resp.json()


def router_status() -> Dict[str, Any]:
    url = _build_get_endpoint(config.CORTENSOR_API_URL, 'status')
    verify = not config.CORTENSOR_TLS_INSECURE
    headers = {'Authorization': f'Bearer {config.CORTENSOR_API_KEY}'}
    resp = requests.get(url, headers=headers, timeout=15, verify=verify)
    resp.raise_for_status()
    return resp.json()


def request_completion(prompt: str, provider: str | None = None, model: str | None = None) -> Dict[str, Any]:
    url = _build_endpoint(config.CORTENSOR_API_URL)
    api_key = config.CORTENSOR_API_KEY
    session_id = config.CORTENSOR_SESSION_ID
    provider = provider or config.MODEL_PROVIDER
    model = model or config.MODEL_NAME
    if not (url and api_key and session_id):
        raise RuntimeError('Cortensor configuration missing. Check .env')

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    # Choose payload schema by endpoint type
    if url.endswith('/api/v1/completions'):
        # Cortensor Web2 REST
        try:
            sess_id = int(str(session_id))
        except Exception:
            raise RuntimeError('CORTENSOR_SESSION_ID must be an integer for /api/v1/completions')
        payload = {
            'session_id': sess_id,
            'prompt': prompt,
            'stream': False,
            'timeout': config.CORTENSOR_TIMEOUT,
        }
    else:
        # Fallback OpenAI-like chat completions
        payload = {
            'provider': provider,
            'model': model,
            'input': prompt,
            'stream': False,
        }
    verify = not config.CORTENSOR_TLS_INSECURE
    def _post(u, p):
        return requests.post(u, headers=headers, data=json.dumps(p), timeout=config.CORTENSOR_TIMEOUT, verify=verify)

    try:
        resp = _post(url, payload)
        if resp.status_code == 404 and url.endswith('/api/v1/completions') and isinstance(payload, dict) and 'session_id' in payload:
            # Try path-param variant: /api/v1/completions/{sessionId}
            alt = url.rstrip('/') + f"/{payload['session_id']}"
            resp = _post(alt, {
                'prompt': payload.get('prompt'),
                'stream': payload.get('stream', False),
                'timeout': payload.get('timeout', config.CORTENSOR_TIMEOUT)
            })
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get('choices'):
            return data
        text = ''
        if isinstance(data, dict):
            text = data.get('output') or data.get('text') or ''
        return {'choices': [{'text': text}]}
    except Exception as e:
        # Sanitize URL for logs: drop scheme, strip query, and mask any userinfo
        safe_url = url.split('://', 1)[-1]
        safe_url = safe_url.split('?', 1)[0]
        safe_url = re.sub(r'^[^@]+@', '***@', safe_url)
        logger.error('Cortensor request failed: %s to %s', e, safe_url)
        raise
