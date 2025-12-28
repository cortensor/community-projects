"""
Cortensor REST API Client
Communicates with local Cortensor Router node via REST API
"""
import logging
import time
import requests
from typing import Dict, Any, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class CortensorClient:
    """
    Client for interacting with Cortensor Router REST API
    """
    
    def __init__(self):
        self.base_url = settings.cortensor_api_url.rstrip('/')
        self.api_key = settings.api_key
        self.session_id = settings.cortensor_session_id
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        logger.info(f"Cortensor Client initialized: {self.base_url}")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"API Key: {'configured' if self.api_key else 'missing'}")
    
    def health_check(self) -> bool:
        """Check if router is reachable"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/completions",
                headers=self.headers,
                timeout=5
            )
            return response.status_code in [200, 405]
        except Exception as e:
            logger.error(f"Router health check failed: {e}")
            return False
    
    def submit_completion(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.95,
        timeout: int = 300  # Increased timeout for async processing
    ) -> Dict[str, Any]:
        """Submit a completion request to Cortensor network"""
        
        if model is None:
            model = settings.cortensor_model_general
        
        payload = {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "session_id": self.session_id
        }
        
        try:
            logger.info(f"Submitting completion to session {self.session_id}")
            logger.info(f"Prompt: {prompt[:100]}...")
            
            response = requests.post(
                f"{self.base_url}/api/v1/completions",
                headers=self.headers,
                json=payload,
                timeout=timeout  # Longer timeout for miner response
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 401:
                logger.error(f"Authentication failed: {response.text}")
                raise PermissionError("Cortensor API authentication failed")
            
            if response.status_code == 404:
                logger.error("Endpoint not found")
                raise ValueError("Cortensor endpoint not found")
            
            response.raise_for_status()
            result = response.json()
            
            # Extract text from response (handle different formats)
            text = ""
            if "choices" in result and len(result["choices"]) > 0:
                text = result["choices"][0].get("text", "")
            elif "text" in result:
                text = result["text"]
            elif "output" in result:
                text = result["output"]
            
            logger.info(f"Completion received: {len(text)} chars")
            logger.info(f"Response preview: {text[:200]}...")
            
            return {
                "text": text,
                "model": result.get("model", model),
                "session_id": result.get("session_id", self.session_id),
                "task_id": result.get("task_id"),
                "usage": result.get("usage", {}),
                "raw": result
            }
        
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after {timeout}s")
            raise TimeoutError(f"Request timed out after {timeout} seconds")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def submit_completion_redundant(
        self,
        prompt: str,
        num_nodes: int = 3,
        model: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Submit completion to multiple nodes (for PoI)"""
        
        if model is None:
            model = settings.cortensor_model_general
        
        # First try the redundant endpoint
        try:
            logger.info(f"Submitting redundant completion ({num_nodes} nodes)")
            
            payload = {
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.95,
                "session_id": self.session_id,
                "n": num_nodes  # Request multiple completions
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/completions",
                headers=self.headers,
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Handle multiple choices
                if "choices" in result:
                    results = []
                    for i, choice in enumerate(result["choices"]):
                        results.append({
                            "text": choice.get("text", ""),
                            "node_index": i,
                            "model": result.get("model", model),
                            "raw": choice
                        })
                    
                    if len(results) >= 2:
                        logger.info(f"Got {len(results)} responses from redundant request")
                        return results
            
            logger.warning("Redundant endpoint didn't return enough results, using fallback")
        
        except Exception as e:
            logger.warning(f"Redundant endpoint failed: {e}, using fallback")
        
        # Fallback: sequential requests
        return self._fallback_sequential(prompt, num_nodes, model, max_tokens, temperature)
    
    def _fallback_sequential(
        self,
        prompt: str,
        num_nodes: int,
        model: str,
        max_tokens: int,
        temperature: float
    ) -> List[Dict[str, Any]]:
        """Fallback: make sequential requests"""
        logger.info(f"Using fallback: {num_nodes} sequential requests")
        
        results = []
        for i in range(num_nodes):
            try:
                logger.info(f"Request {i+1}/{num_nodes}...")
                result = self.submit_completion(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=300
                )
                result['node_index'] = i
                results.append(result)
                logger.info(f"Response {i+1}/{num_nodes} received: {len(result.get('text', ''))} chars")
                
                # Small delay between requests
                if i < num_nodes - 1:
                    time.sleep(1)
                    
            except Exception as e:
                logger.warning(f"Request {i+1} failed: {e}")
        
        return results
    
    def submit_validation(
        self,
        prompt: str,
        num_validators: int = 1,
        model: str = None
    ) -> List[Dict[str, Any]]:
        """Submit validation requests (for PoUW)"""
        
        if model is None:
            model = settings.cortensor_model_reasoning
        
        logger.info(f"Submitting {num_validators} validation requests")
        
        results = []
        for i in range(num_validators):
            try:
                result = self.submit_completion(
                    prompt=prompt,
                    model=model,
                    max_tokens=100,
                    temperature=0.3,
                    timeout=300
                )
                result['validator_index'] = i
                results.append(result)
                logger.info(f"Validation {i+1}/{num_validators} received")
                
                if i < num_validators - 1:
                    time.sleep(1)
                    
            except Exception as e:
                logger.warning(f"Validation {i+1} failed: {e}")
        
        return results
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session info"""
        return {
            "session_id": self.session_id,
            "api_url": self.base_url,
            "status": "active"
        }


# Global client instance
cortensor_client = CortensorClient()