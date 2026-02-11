"""
Proof of Useful Work (PoUW) Engine
Validates output quality through multi-node consensus
"""
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from backend.cortensor_client import cortensor_client
from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PoUWResult:
    """Result of PoUW validation"""
    is_valid: bool
    quality_score: float  # 0.0 to 1.0
    validator_scores: List[float]
    consensus_reached: bool
    validation_details: Dict[str, Any]


class PoUWEngine:
    """
    Proof of Useful Work validation engine
    Uses multiple validator nodes to assess output quality
    """
    
    def __init__(self):
        self.num_validators = settings.pouw_num_validators
        self.quality_threshold = settings.pouw_quality_threshold
        self.consensus_threshold = settings.pouw_consensus_threshold
    
    def validate(
        self,
        task_description: str,
        task_input: str,
        agent_output: str,
        num_validators: int = None
    ) -> PoUWResult:
        """
        Validate agent output quality using multiple validators
        """
        if num_validators is None:
            num_validators = self.num_validators
        
        logger.info(f"PoUW validation with {num_validators} validators")
        
        if not agent_output or len(agent_output.strip()) == 0:
            logger.warning("Empty agent output - returning failed validation")
            return PoUWResult(
                is_valid=False,
                quality_score=0.0,
                validator_scores=[],
                consensus_reached=False,
                validation_details={"error": "Empty output"}
            )
        
        # Define validation criteria
        criteria = [
            ("CORRECTNESS", "Is the output factually correct and accurate?"),
            ("COMPLETENESS", "Does the output fully address the task requirements?"),
            ("CLARITY", "Is the output clear and well-structured?"),
        ]
        
        all_scores = []
        criteria_scores = {}
        
        for criterion_name, criterion_desc in criteria:
            scores = self._validate_criterion(
                task_description=task_description,
                task_input=task_input,
                agent_output=agent_output,
                criterion_name=criterion_name,
                criterion_desc=criterion_desc,
                num_validators=num_validators
            )
            
            if scores:
                criteria_scores[criterion_name] = {
                    "scores": scores,
                    "average": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores)
                }
                all_scores.extend(scores)
        
        if not all_scores:
            logger.warning("No validation scores received")
            return PoUWResult(
                is_valid=False,
                quality_score=0.0,
                validator_scores=[],
                consensus_reached=False,
                validation_details={"error": "No validator responses"}
            )
        
        # Calculate overall quality score
        quality_score = sum(all_scores) / len(all_scores) / 10.0  # Normalize to 0-1
        
        # Check consensus (are validators in agreement?)
        score_variance = self._calculate_variance(all_scores)
        consensus_reached = score_variance < 2.0  # Low variance = consensus
        
        # Determine validity
        is_valid = quality_score >= self.quality_threshold and consensus_reached
        
        logger.info(f"PoUW result: score={quality_score:.2f}, consensus={consensus_reached}, valid={is_valid}")
        
        return PoUWResult(
            is_valid=is_valid,
            quality_score=quality_score,
            validator_scores=all_scores,
            consensus_reached=consensus_reached,
            validation_details={
                "criteria_scores": criteria_scores,
                "score_variance": score_variance,
                "num_validators": num_validators
            }
        )
    
    def _validate_criterion(
        self,
        task_description: str,
        task_input: str,
        agent_output: str,
        criterion_name: str,
        criterion_desc: str,
        num_validators: int
    ) -> List[float]:
        """Validate a single criterion using multiple validators"""
        
        # Truncate output if too long
        output_preview = agent_output[:500] + "..." if len(agent_output) > 500 else agent_output
        
        prompt = f"""Rate the {criterion_name} of this AI output on a scale of 1-10.

Task: {task_description}
Input: {task_input}
Output: {output_preview}

Criteria: {criterion_desc}

Respond with ONLY a number from 1-10:"""
        
        scores = []
        
        for i in range(num_validators):
            try:
                # Use regular completions endpoint (not validations)
                result = cortensor_client.submit_completion(
                    prompt=prompt,
                    model=settings.cortensor_model_reasoning,
                    max_tokens=50,
                    temperature=0.3,
                    timeout=180
                )
                
                text = result.get("text", "").strip()
                score = self._extract_score(text)
                
                if score is not None:
                    scores.append(score)
                    logger.debug(f"Validator {i+1} score for {criterion_name}: {score}")
                else:
                    logger.warning(f"Validator {i+1} returned invalid score: {text}")
                    
            except Exception as e:
                logger.warning(f"Validator {i+1} failed for {criterion_name}: {e}")
        
        return scores
    
    def _extract_score(self, text: str) -> Optional[float]:
        """Extract numeric score from validator response"""
        # Try to find a number in the response
        numbers = re.findall(r'\b([1-9]|10)\b', text)
        if numbers:
            return float(numbers[0])
        
        # Try to parse as float
        try:
            text_clean = text.strip().split()[0] if text.strip() else ""
            score = float(text_clean)
            if 1 <= score <= 10:
                return score
        except (ValueError, IndexError):
            pass
        
        return None
    
    def _calculate_variance(self, scores: List[float]) -> float:
        """Calculate variance of scores"""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        return variance


# Global engine instance
pouw_engine = PoUWEngine()
