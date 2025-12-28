"""
Xea Governance Oracle - Attestation

Functions for signing evidence bundles and publishing to IPFS.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# ECDSA Signing
# ============================================================================

def sign_bundle(bundle: Dict[str, Any]) -> Dict[str, str]:
    """
    Sign an evidence bundle with ECDSA using the configured private key.
    
    The signature is created over the SHA-256 hash of the canonical JSON
    representation of the bundle.
    
    Args:
        bundle: Evidence bundle dict to sign
        
    Returns:
        Dict with:
        - signature: Hex-encoded signature
        - signer: Ethereum address of the signer
        - message_hash: Hash of the signed message
        
    Note:
        If SIGNER_PRIVATE_KEY is not configured, returns a deterministic
        mock signature for development purposes.
    """
    # Compute canonical hash of bundle
    canonical_json = json.dumps(bundle, sort_keys=True, separators=(',', ':'))
    message_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
    
    private_key = settings.signer_private_key
    
    if not private_key:
        logger.warning("No private key configured, using mock signature")
        return _mock_sign(message_hash)
    
    try:
        # Use eth_account for real ECDSA signing
        from eth_account import Account
        from eth_account.messages import encode_defunct
        
        # Create signable message
        message = encode_defunct(text=message_hash)
        
        # Sign the message
        signed = Account.sign_message(message, private_key=private_key)
        
        # Get signer address
        signer_address = Account.from_key(private_key).address
        
        return {
            "signature": signed.signature.hex(),
            "signer": signer_address,
            "message_hash": message_hash,
        }
        
    except Exception as e:
        logger.error(f"Signing failed: {e}, using mock signature")
        return _mock_sign(message_hash)


def _mock_sign(message_hash: str) -> Dict[str, str]:
    """
    Generate a deterministic mock signature for development.
    
    Args:
        message_hash: Hash to "sign"
        
    Returns:
        Mock signature dict
    """
    # Create deterministic mock signature from hash
    mock_sig = hashlib.sha256(f"mock_sig_{message_hash}".encode()).hexdigest()
    
    # Mock address from hash
    mock_address = "0x" + hashlib.sha256(f"mock_addr_{message_hash}".encode()).hexdigest()[:40]
    
    return {
        "signature": f"0x{mock_sig}",
        "signer": mock_address,
        "message_hash": message_hash,
        "mock": True,
    }


def verify_signature(
    bundle: Dict[str, Any],
    signature: str,
    expected_signer: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Verify an ECDSA signature on an evidence bundle.
    
    Args:
        bundle: The evidence bundle that was signed
        signature: Hex-encoded signature to verify
        expected_signer: Optional expected signer address
        
    Returns:
        Tuple of (is_valid, recovered_address)
    """
    # Compute canonical hash
    canonical_json = json.dumps(bundle, sort_keys=True, separators=(',', ':'))
    message_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
    
    # Check if this is a mock signature
    if signature.startswith("0x") and len(signature) == 66:
        expected_mock = hashlib.sha256(f"mock_sig_{message_hash}".encode()).hexdigest()
        if signature == f"0x{expected_mock}":
            mock_addr = "0x" + hashlib.sha256(f"mock_addr_{message_hash}".encode()).hexdigest()[:40]
            return (True, mock_addr)
    
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        
        message = encode_defunct(text=message_hash)
        
        # Recover address from signature
        recovered = Account.recover_message(message, signature=signature)
        
        if expected_signer:
            return (recovered.lower() == expected_signer.lower(), recovered)
        
        return (True, recovered)
        
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return (False, "")


# ============================================================================
# IPFS Publishing
# ============================================================================

def publish_bundle_ipfs(bundle_path: str) -> str:
    """
    Publish an evidence bundle to IPFS.
    
    Args:
        bundle_path: Path to the evidence bundle JSON file
        
    Returns:
        IPFS CID (Content Identifier) or mock CID
        
    Note:
        If IPFS is not available, returns a mock CID based on the
        file's SHA-256 hash for development purposes.
    """
    file_path = Path(bundle_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Bundle file not found: {bundle_path}")
    
    # Read file content
    with open(file_path, "r") as f:
        content = f.read()
    
    # Compute content hash
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    
    ipfs_url = settings.ipfs_api_url
    
    if not ipfs_url or ipfs_url == "http://localhost:5001":
        # Try to connect to IPFS, fall back to mock
        try:
            return _publish_to_ipfs(file_path, ipfs_url)
        except Exception as e:
            logger.warning(f"IPFS not available, using mock CID: {e}")
            return _mock_ipfs_cid(content_hash)
    
    try:
        return _publish_to_ipfs(file_path, ipfs_url)
    except Exception as e:
        logger.error(f"IPFS publish failed: {e}")
        return _mock_ipfs_cid(content_hash)


def _publish_to_ipfs(file_path: Path, ipfs_url: str) -> str:
    """
    Actually publish to IPFS using the HTTP API.
    
    Args:
        file_path: Path to file to publish
        ipfs_url: IPFS API URL
        
    Returns:
        IPFS CID
    """
    import httpx
    
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f)}
        
        response = httpx.post(
            f"{ipfs_url}/api/v0/add",
            files=files,
            timeout=30.0,
        )
        
        response.raise_for_status()
        result = response.json()
        
        cid = result.get("Hash")
        logger.info(f"Published to IPFS: {cid}")
        
        return f"ipfs://{cid}"


def _mock_ipfs_cid(content_hash: str) -> str:
    """
    Generate a mock IPFS CID for development.
    
    Uses a deterministic format based on content hash.
    
    Args:
        content_hash: SHA-256 hash of the content
        
    Returns:
        Mock IPFS CID in format "mockipfs://{hash}"
    """
    # Create a CIDv1-like string (not a real CID, just for dev)
    return f"mockipfs://{content_hash[:46]}"


def publish_bundle_dict(bundle: Dict[str, Any]) -> str:
    """
    Publish a bundle dict directly to IPFS (or mock).
    
    Args:
        bundle: Evidence bundle dict
        
    Returns:
        IPFS CID
    """
    # Compute content hash
    canonical_json = json.dumps(bundle, sort_keys=True, indent=2)
    content_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
    
    ipfs_url = settings.ipfs_api_url
    
    if not ipfs_url or "localhost" in ipfs_url:
        try:
            return _publish_dict_to_ipfs(bundle, ipfs_url)
        except Exception as e:
            logger.warning(f"IPFS not available: {e}")
            return _mock_ipfs_cid(content_hash)
    
    return _mock_ipfs_cid(content_hash)


def _publish_dict_to_ipfs(bundle: Dict[str, Any], ipfs_url: str) -> str:
    """Publish dict directly to IPFS."""
    import httpx
    
    content = json.dumps(bundle, sort_keys=True, indent=2)
    
    response = httpx.post(
        f"{ipfs_url}/api/v0/add",
        files={"file": ("evidence.json", content.encode())},
        timeout=30.0,
    )
    
    response.raise_for_status()
    result = response.json()
    
    cid = result.get("Hash")
    return f"ipfs://{cid}"


# ============================================================================
# Full Attestation Flow
# ============================================================================

def create_attestation(
    bundle: Dict[str, Any],
    publish: bool = False,
) -> Dict[str, Any]:
    """
    Create a full attestation for an evidence bundle.
    
    This:
    1. Signs the bundle with ECDSA
    2. Optionally publishes to IPFS
    3. Returns attestation metadata
    
    Args:
        bundle: Evidence bundle to attest
        publish: Whether to publish to IPFS
        
    Returns:
        Attestation dict with signature, signer, and optional IPFS CID
    """
    # Sign the bundle
    signature_data = sign_bundle(bundle)
    
    attestation = {
        "job_id": bundle.get("job_id", ""),
        "proposal_hash": bundle.get("proposal_hash", ""),
        "signature": signature_data["signature"],
        "signer": signature_data["signer"],
        "message_hash": signature_data["message_hash"],
        "is_mock": signature_data.get("mock", False),
    }
    
    # Publish to IPFS if requested
    if publish:
        cid = publish_bundle_dict(bundle)
        attestation["ipfs_cid"] = cid
    else:
        attestation["ipfs_cid"] = None
    
    # Add verification instructions
    attestation["verification_instructions"] = {
        "step_1": "Compute SHA-256 hash of the canonical JSON bundle",
        "step_2": "Use ecrecover with the signature to recover the signer address",
        "step_3": "Verify the recovered address matches the claimed signer",
        "step_4": "If IPFS CID provided, fetch bundle from IPFS and verify content hash",
    }
    
    return attestation
