"""
Web3 client for interacting with Cortensor contracts on Arbitrum Sepolia
"""
import json
import time
import logging
from pathlib import Path
from web3 import Web3
from eth_account import Account
from typing import Dict, Any, List, Tuple

from backend.config import settings

logger = logging.getLogger(__name__)


class CortensorWeb3Client:
    """Client for interacting with Cortensor SessionV2 and SessionQueueV2 contracts"""
    
    def __init__(self):
        # Connect to Arbitrum Sepolia
        self.w3 = Web3(Web3.HTTPProvider(settings.arbitrum_sepolia_rpc_url))
        
        # Add PoA middleware for Arbitrum compatibility (web3.py v7+ compatible)
        try:
            # Try web3.py v7+ method
            from web3.middleware import ExtraDataToPOAMiddleware
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        except ImportError:
            try:
                # Fallback for web3.py v6.x
                from web3.middleware import geth_poa_middleware
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            except ImportError:
                # No middleware needed for some versions
                logger.warning("Could not load PoA middleware, continuing without it")
        
        # Load account from private key (if provided)
        if settings.private_key:
            self.account = Account.from_key(settings.private_key)
            self.w3.eth.default_account = self.account.address
        else:
            self.account = None
            logger.warning("No private key provided - read-only mode")
        
        # Load contract ABIs
        abi_dir = Path(__file__).parent.parent
        
        try:
            with open(abi_dir / "SessionV2ABI.json", "r") as f:
                session_v2_abi = json.load(f)
            with open(abi_dir / "SessionQueueV2ABI.json", "r") as f:
                session_queue_v2_abi = json.load(f)
            
            # Initialize contract instances
            if settings.session_v2_address:
                self.session_v2 = self.w3.eth.contract(
                    address=Web3.to_checksum_address(settings.session_v2_address),
                    abi=session_v2_abi
                )
            else:
                self.session_v2 = None
                
            if settings.session_queue_v2_address:
                self.session_queue_v2 = self.w3.eth.contract(
                    address=Web3.to_checksum_address(settings.session_queue_v2_address),
                    abi=session_queue_v2_abi
                )
            else:
                self.session_queue_v2 = None
                
        except FileNotFoundError as e:
            logger.warning(f"ABI files not found: {e}")
            self.session_v2 = None
            self.session_queue_v2 = None
        
        logger.info(f"Web3 client initialized. Connected: {self.w3.is_connected()}")
        if self.account:
            logger.info(f"Account address: {self.account.address}")
    
    def create_session(
        self,
        session_name: str,
        model: str,
        redundant: int = 3,
        num_validators: int = 0,
        task_timeout: int = 180
    ) -> Tuple[int, str]:
        """Create a new Cortensor session"""
        
        # Check for pre-configured session ID
        if settings.cortensor_session_id > 0:
            logger.info(f"Using existing Session ID: {settings.cortensor_session_id}")
            return settings.cortensor_session_id, "0x0"
        
        if not self.session_v2 or not self.account:
            raise ValueError("Web3 client not properly configured for transactions")
        
        try:
            tx = self.session_v2.functions.create(
                session_name,
                model,
                self.account.address,
                redundant,
                redundant,
                redundant,
                num_validators,
                0,
                False
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            session_created_event = self.session_v2.events.SessionCreated().process_receipt(receipt)
            session_id = session_created_event[0]['args']['sessionId']
            
            logger.info(f"Session created: ID={session_id}, TX={tx_hash.hex()}")
            return session_id, tx_hash.hex()
        
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def submit_task(self, session_id: int, prompt: str, model_params: Dict[str, Any] = None) -> Tuple[int, str]:
        """Submit a task to an existing session"""
        
        if not self.session_v2 or not self.account:
            raise ValueError("Web3 client not properly configured for transactions")
        
        try:
            if model_params is None:
                llm_params = [2048, 700, 950, 50, 0, 0]
            else:
                llm_params = [
                    model_params.get('max_tokens', 2048),
                    int(model_params.get('temperature', 0.7) * 1000),
                    int(model_params.get('top_p', 0.95) * 1000),
                    model_params.get('top_k', 50),
                    int(model_params.get('presence_penalty', 0) * 1000),
                    int(model_params.get('frequency_penalty', 0) * 1000)
                ]
            
            tx = self.session_v2.functions.submit(
                session_id,
                0,
                prompt,
                0,
                "",
                llm_params,
                ""
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            task_submitted_event = self.session_v2.events.TaskSubmitted().process_receipt(receipt)
            task_id = task_submitted_event[0]['args']['taskId']
            
            logger.info(f"Task submitted: Session={session_id}, Task={task_id}")
            return task_id, tx_hash.hex()
        
        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            raise
    
    def get_task_results(self, session_id: int, task_id: int) -> List[Dict[str, Any]]:
        """Retrieve all results for a task"""
        
        if not self.session_queue_v2:
            raise ValueError("SessionQueueV2 contract not configured")
        
        try:
            miners, outputs = self.session_queue_v2.functions.getTaskResults(
                session_id,
                task_id
            ).call()
            
            results = []
            for miner, output in zip(miners, outputs):
                results.append({
                    'miner': miner,
                    'output': output
                })
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to get task results: {e}")
            raise
    
    def get_session_info(self, session_id: int) -> Dict[str, Any]:
        """Get detailed session information"""
        
        if not self.session_v2:
            return {"session_id": session_id, "status": "unknown"}
        
        try:
            session = self.session_v2.functions.getSession(session_id).call()
            return {
                'id': session[0],
                'name': session[2],
                'state': session[4],
                'redundant': session[11]
            }
        except Exception as e:
            logger.error(f"Failed to get session info: {e}")
            return {"session_id": session_id, "error": str(e)}
    
    def deactivate_session(self, session_id: int) -> str:
        """Deactivate a session after use"""
        
        # Don't deactivate the shared session
        if settings.cortensor_session_id > 0 and session_id == settings.cortensor_session_id:
            logger.info(f"Skipping deactivation of shared session {session_id}")
            return "0x0"
        
        if not self.session_v2 or not self.account:
            return "0x0"
        
        try:
            tx = self.session_v2.functions.deactivateSession(
                session_id
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            logger.info(f"Session {session_id} deactivated")
            return tx_hash.hex()
        
        except Exception as e:
            logger.warning(f"Failed to deactivate session: {e}")
            return "0x0"


# Global client instance
web3_client = CortensorWeb3Client()
