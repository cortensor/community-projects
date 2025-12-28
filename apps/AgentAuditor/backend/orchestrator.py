"""
Audit Orchestrator
Coordinates the audit pipeline: PoI → PoUW → Evidence Generation
"""
import logging
import time
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.engines.poi_engine import poi_engine
from backend.engines.pouw_engine import pouw_engine
from backend.engines.evidence_generator import EvidenceBundleGenerator
from backend.config import settings
from backend.database import get_db_context
from backend.models import Agent, Audit

logger = logging.getLogger(__name__)


class AuditOrchestrator:
    """
    Orchestrates the complete audit pipeline
    """
    
    def __init__(self):
        self.poi_engine = poi_engine
        self.pouw_engine = pouw_engine
        self.evidence_generator = EvidenceBundleGenerator()
    
    async def run_audit(
        self,
        agent_id: str,
        agent_name: Optional[str],
        task_description: str,
        task_input: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Run complete audit pipeline
        """
        audit_id = f"aud_{secrets.token_hex(6)}"
        
        logger.info(f"Starting audit {audit_id} for agent {agent_id}")
        
        start_time = time.time()
        
        try:
            # Ensure agent exists in database
            self._ensure_agent_exists(agent_id, agent_name)  # REMOVED await
            
            # Step 1: Build the full prompt for the agent
            full_prompt = self._build_agent_prompt(task_description, task_input)
            logger.info(f"[{audit_id}] Full prompt: {full_prompt[:200]}...")
            
            # Step 2: Run PoI - Get responses from multiple nodes
            logger.info(f"[{audit_id}] Running PoI validation...")
            poi_result = self.poi_engine.submit_and_validate(
                prompt=full_prompt,
                num_nodes=settings.poi_num_nodes,
                similarity_threshold=settings.poi_similarity_threshold
            )
            
            if not poi_result.get('passed') or not poi_result.get('consensus_output'):
                logger.error(f"[{audit_id}] PoI validation failed")
                return self._create_failed_result(  # REMOVED await
                    audit_id=audit_id,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    task_description=task_description,
                    task_input=task_input,
                    category=category,
                    error="PoI validation failed - inconsistent or no responses",
                    poi_result=poi_result
                )
            
            # Get the agent's output (canonical response from PoI)
            agent_output = poi_result.get('consensus_output', '')
            logger.info(f"[{audit_id}] Agent output: {agent_output[:200]}...")
            
            # Step 3: Run PoUW - Validate the quality of the output
            logger.info(f"[{audit_id}] Running PoUW validation...")
            pouw_result = self.pouw_engine.validate(
                task_description=task_description,
                task_input=task_input,
                agent_output=agent_output,
                num_validators=settings.pouw_num_validators
            )
            
            # Step 4: Calculate final confidence score
            poi_similarity = poi_result.get('similarity_score', 0.0)
            pouw_score = pouw_result.quality_score
            
            confidence_score = self.evidence_generator.calculate_final_confidence(
                poi_similarity=poi_similarity,
                pouw_score=pouw_score
            )
            
            # Step 5: Generate evidence bundle
            logger.info(f"[{audit_id}] Generating evidence...")
            
            # Convert PoUW result to dict for evidence
            pouw_result_dict = {
                'is_valid': pouw_result.is_valid,
                'overall_score': pouw_result.quality_score,
                'overall_score_raw': pouw_result.quality_score * 10,
                'passed': pouw_result.is_valid,
                'num_validators': len(pouw_result.validator_scores),
                'criterion_scores': pouw_result.validation_details.get('criteria_scores', {})
            }
            
            evidence = self.evidence_generator.generate_bundle(
                audit_id=audit_id,
                agent_id=agent_id,
                task_description=task_description,
                task_input=task_input,
                poi_result=poi_result,
                pouw_result=pouw_result_dict,
                final_confidence=confidence_score
            )
            
            # Step 6: Save audit to database
            self._save_audit(  # REMOVED await
                audit_id=audit_id,
                agent_id=agent_id,
                agent_name=agent_name,
                task_description=task_description,
                task_input=task_input,
                category=category,
                poi_similarity=poi_similarity,
                pouw_score=pouw_score,
                confidence_score=confidence_score,
                status="completed",
                ipfs_cid=evidence.get('ipfs_cid'),
                evidence_hash=evidence.get('bundle_hash')
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"[{audit_id}] Audit completed in {elapsed_time:.2f}s")
            
            return {
                "audit_id": audit_id,
                "agent_id": agent_id,
                "status": "completed",
                "confidence_score": confidence_score,
                "poi_similarity": poi_similarity,
                "pouw_mean_score": pouw_score,
                "ipfs_cid": evidence.get('ipfs_cid'),
                "timestamp": datetime.utcnow().isoformat(),
                "elapsed_time": elapsed_time
            }
            
        except Exception as e:
            logger.error(f"[{audit_id}] Audit failed: {str(e)}", exc_info=True)
            return self._create_failed_result(  # REMOVED await
                audit_id=audit_id,
                agent_id=agent_id,
                agent_name=agent_name,
                task_description=task_description,
                task_input=task_input,
                category=category,
                error=str(e)
            )
    
    def _build_agent_prompt(self, task_description: str, task_input: str) -> str:
        """Build the full prompt to send to the agent"""
        # Enhanced prompt with clearer instructions for code generation
        system_context = """You are an AI assistant that follows instructions precisely.
If asked to write code, respond with ONLY the code - no explanations, no markdown formatting, no comments unless specifically requested.
If given an input value, use it as a test case reference but still provide the complete solution as requested."""
        
        if task_input and task_input.strip():
            return f"""{system_context}

Task: {task_description}

Example Input: {task_input}

Output:"""
        else:
            return f"""{system_context}

Task: {task_description}

Output:"""
    
    def _ensure_agent_exists(self, agent_id: str, agent_name: Optional[str]):  # REMOVED async
        """Ensure agent exists in database"""
        with get_db_context() as db:
            agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
            if not agent:
                agent = Agent(
                    agent_id=agent_id,
                    name=agent_name or agent_id
                )
                db.add(agent)
                # Commit is handled by context manager
    
    def _save_audit(  # REMOVED async
        self,
        audit_id: str,
        agent_id: str,
        agent_name: Optional[str],
        task_description: str,
        task_input: str,
        category: str,
        poi_similarity: float,
        pouw_score: float,
        confidence_score: float,
        status: str,
        ipfs_cid: Optional[str] = None,
        evidence_hash: Optional[str] = None
    ):
        """Save audit to database"""
        with get_db_context() as db:
            audit = Audit(
                audit_id=audit_id,
                agent_id=agent_id,
                agent_name=agent_name,
                task_description=task_description,
                task_input=task_input,
                category=category,
                poi_similarity=poi_similarity,
                pouw_mean_score=pouw_score,
                final_confidence=confidence_score,
                status=status,
                ipfs_cid=ipfs_cid,
                evidence_hash=evidence_hash,
                timestamp=datetime.utcnow(),
                completed_at=datetime.utcnow() if status == "completed" else None
            )
            db.add(audit)
            # Commit handled by context manager
    
    def _create_failed_result(  # REMOVED async
        self,
        audit_id: str,
        agent_id: str,
        agent_name: Optional[str],
        task_description: str,
        task_input: str,
        category: str,
        error: str,
        poi_result: Dict = None
    ) -> Dict[str, Any]:
        """Create a failed audit result"""
        # Save failed audit to database
        with get_db_context() as db:
            audit = Audit(
                audit_id=audit_id,
                agent_id=agent_id,
                agent_name=agent_name,
                task_description=task_description,
                task_input=task_input,
                category=category,
                status="failed",
                final_confidence=0.0,
                poi_similarity=poi_result.get('similarity_score', 0.0) if poi_result else 0.0,
                pouw_mean_score=0.0,
                timestamp=datetime.utcnow()
            )
            db.add(audit)
            # Commit handled by context manager
        
        return {
            "audit_id": audit_id,
            "agent_id": agent_id,
            "status": "failed",
            "error": error,
            "confidence_score": 0.0,
            "poi_similarity": poi_result.get('similarity_score', 0.0) if poi_result else 0.0,
            "pouw_mean_score": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_audit_status(self, audit_id: str) -> Dict[str, Any]:
        """Get audit status and results"""
        with get_db_context() as db:
            audit = db.query(Audit).filter(Audit.audit_id == audit_id).first()
            if not audit:
                raise ValueError(f"Audit {audit_id} not found")
            
            return {
                "audit_id": audit.audit_id,
                "agent_id": audit.agent_id,
                "status": audit.status,
                "confidence_score": audit.final_confidence,
                "poi_similarity": audit.poi_similarity,
                "pouw_score": audit.pouw_mean_score,
                "timestamp": audit.timestamp.isoformat() if audit.timestamp else None
            }


# Global orchestrator instance
orchestrator = AuditOrchestrator()
