"""
IPFS integration for storing evidence bundles
Supports Pinata and Web3.Storage providers
"""
import json
import requests
import logging
from typing import Dict, Any, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class IPFSClient:
    """Client for uploading evidence bundles to IPFS"""
    
    def __init__(self):
        self.provider = settings.ipfs_provider
        logger.info(f"IPFS client initialized with provider: {self.provider}")
    
    def upload_bundle(self, bundle: Dict[str, Any]) -> str:
        """
        Upload evidence bundle to IPFS
        
        Args:
            bundle: Evidence bundle dictionary
        
        Returns:
            IPFS hash (CID)
        """
        if self.provider == "pinata":
            return self._upload_pinata(bundle)
        elif self.provider == "web3storage":
            return self._upload_web3storage(bundle)
        else:
            raise ValueError(f"Unsupported IPFS provider: {self.provider}")
    
    def _upload_pinata(self, bundle: Dict[str, Any]) -> str:
        """
        Upload to Pinata IPFS service
        
        Args:
            bundle: Evidence bundle
        
        Returns:
            IPFS hash
        """
        url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
        
        headers = {
            "pinata_api_key": settings.pinata_api_key,
            "pinata_secret_api_key": settings.pinata_secret_key
        }
        
        payload = {
            "pinataContent": bundle,
            "pinataMetadata": {
                "name": f"cortensor-audit-{bundle['audit_id']}",
                "keyvalues": {
                    "audit_id": bundle['audit_id'],
                    "agent_id": bundle['agent_id'],
                    "confidence": str(bundle['final_assessment']['confidence_score'])
                }
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            ipfs_hash = result['IpfsHash']
            
            logger.info(f"Bundle uploaded to Pinata: {ipfs_hash}")
            return ipfs_hash
        
        except Exception as e:
            logger.error(f"Failed to upload to Pinata: {e}")
            raise
    
    def _upload_web3storage(self, bundle: Dict[str, Any]) -> str:
        """
        Upload to Web3.Storage IPFS service
        
        Args:
            bundle: Evidence bundle
        
        Returns:
            IPFS hash
        """
        url = "https://api.web3.storage/upload"
        
        headers = {
            "Authorization": f"Bearer {settings.web3_storage_token}",
            "Content-Type": "application/json"
        }
        
        try:
            bundle_json = json.dumps(bundle)
            
            response = requests.post(url, data=bundle_json, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            ipfs_hash = result['cid']
            
            logger.info(f"Bundle uploaded to Web3.Storage: {ipfs_hash}")
            return ipfs_hash
        
        except Exception as e:
            logger.error(f"Failed to upload to Web3.Storage: {e}")
            raise
    
    def retrieve_bundle(self, ipfs_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve evidence bundle from IPFS
        
        Args:
            ipfs_hash: IPFS CID
        
        Returns:
            Bundle dictionary or None if not found
        """
        # Use public IPFS gateway
        gateways = [
            f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}",
            f"https://ipfs.io/ipfs/{ipfs_hash}",
            f"https://cloudflare-ipfs.com/ipfs/{ipfs_hash}"
        ]
        
        for gateway in gateways:
            try:
                response = requests.get(gateway, timeout=10)
                response.raise_for_status()
                
                bundle = response.json()
                logger.info(f"Bundle retrieved from IPFS: {ipfs_hash}")
                return bundle
            
            except Exception as e:
                logger.warning(f"Failed to retrieve from {gateway}: {e}")
                continue
        
        logger.error(f"Failed to retrieve bundle from all gateways: {ipfs_hash}")
        return None


# Global IPFS client instance
ipfs_client = IPFSClient()
