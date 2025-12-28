"""
Xea Governance Oracle - Cortensor Testnet Client

This module is the EXCLUSIVE gateway to the Real Cortensor Testnet.
It handles all decentralized inference requests via the official Cortensor Router.

Strict requirements:
- No mocks.
- Real HTTP calls to the Router.
- Mandatory Authentication.
"""

import httpx
import logging
import asyncio
import json
from typing import Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


async def validate_with_cortensor(
    system_prompt: str,
    user_prompt: str,
    rubric: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate a prompt using Real Cortensor Testnet infrastructure.
    
    Sends a request to the decentralized network via the Router.
    Explicitly requests Proof of Inference (PoI) and Proof of Useful Work (PoUW).
    
    Args:
        system_prompt: Context and instructions for the miner
        user_prompt: The specific claim to validate
        rubric: Scoring rubric for PoUW
        
    Returns:
        Raw JSON response from Cortensor Router (unaltered)
        
    Raises:
        ValueError: If configuration is missing
        httpx.HTTPError: If network request fails after retries
    """
    # 1. Strict Configuration Check
    if not all([settings.cortensor_router_url, settings.cortensor_api_key, settings.cortensor_session_id]):
        error_msg = (
            "Missing mandatory Cortensor Testnet configuration. "
            "Ensure CORTENSOR_ROUTER_URL, CORTENSOR_API_KEY, and CORTENSOR_SESSION_ID are set."
        )
        logger.critical(error_msg)
        raise ValueError(error_msg)

    # 2. Build Endpoint URL
    # Format: {ROUTER_URL}/api/v1/completions/{SESSION_ID}
    base_url = settings.cortensor_router_url.rstrip("/")
    session_id = settings.cortensor_session_id
    url = f"{base_url}/api/v1/completions/{session_id}"
    
    # 3. Use API Key Directly (UUID format, no 0x prefix needed)
    auth_candidates = [settings.cortensor_api_key] if settings.cortensor_api_key else []
    
    # Common Headers
    headers = {
        "Content-Type": "application/json",
        "X-Cortensor-Client": "Xea-Oracle/1.0.0"
    }

    # Payload
    payload = {
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": f"cortensor-{settings.cortensor_network}",
        "temperature": 0.1,
        "proof_of_inference": True,
        "proof_of_useful_work": True,
        "pouw_rubric": rubric,
        "stream": False 
    }
    
    max_retries = 2
    timeout = 120.0
    last_error = None

    # 4. Iterate through Auth Candidates
    async with httpx.AsyncClient(timeout=timeout) as client:
        for token in auth_candidates:
            # Set Auth Header
            headers["Authorization"] = f"Bearer {token}"
            masked = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else token
            
            # Retry loop for NETWORK errors (not Auth errors)
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"Sending request to Cortensor (Session: {session_id}, Key: {masked}, Attempt: {attempt+1})")
                    
                    response = await client.post(url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Auth Success with token: {masked}")
                        return response.json()
                    
                    elif response.status_code == 401:
                        logger.warning(f"❌ Auth Failed (401) with token: {masked}")
                        last_error = f"401 Unauthorized with token {masked}"
                        break # Break inner retry loop, try next token
                        
                    elif response.status_code == 429:
                        # Rate limit - wait and retry same token
                        retry_after = int(response.headers.get("Retry-After", 1))
                        logger.warning(f"Rate limited. Waiting {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    else:
                        # Other server errors (500, etc) - retry same token
                        response.raise_for_status()
                
                except httpx.HTTPError as e:
                    logger.warning(f"Network error with token {masked}: {e}")
                    last_error = str(e)
                    if attempt < max_retries:
                        await asyncio.sleep(1 * (2 ** attempt))
                    else:
                        break # Give up on this token if network is persistently broken

    # If we exhaust all candidates or network fails
    logger.error("All Cortensor Auth/Network attempts failed.")
    raise ValueError(f"Cortensor Validation Failed. Last error: {last_error}")
