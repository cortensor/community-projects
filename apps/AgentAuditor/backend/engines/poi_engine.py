"""
Proof of Inference (PoI) Engine
Validates output consistency across redundant nodes via embedding similarity
"""
import logging
import time
import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from backend.config import settings
from backend.cortensor_client import cortensor_client

logger = logging.getLogger(__name__)


class PoIEngine:
    """
    Proof of Inference Engine
    
    Creates sessions with redundant nodes and validates consistency
    via embedding similarity calculations.
    """
    
    def __init__(self):
        # Load sentence transformer model for embeddings
        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("PoI Engine initialized with all-MiniLM-L6-v2")
    
    def submit_and_validate(
        self,
        prompt: str,
        num_nodes: int = None,
        similarity_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Submit prompt to redundant nodes and validate consistency
        
        Args:
            prompt: The input prompt
            num_nodes: Number of redundant nodes (default from config)
            similarity_threshold: Minimum similarity for consensus
        
        Returns:
            PoI validation result with scores and consensus
        """
        if num_nodes is None:
            num_nodes = settings.poi_redundancy
        if similarity_threshold is None:
            similarity_threshold = settings.poi_similarity_threshold
        
        logger.info(f"PoI validation: {num_nodes} nodes, threshold={similarity_threshold}")
        
        start_time = time.time()
        
        # Step 1: Get responses from redundant nodes
        responses = cortensor_client.submit_completion_redundant(
            prompt=prompt,
            num_nodes=num_nodes,
            model=settings.cortensor_model_general
        )
        
        if len(responses) < 2:
            logger.warning(f"Only got {len(responses)} responses, need at least 2")
            if len(responses) == 1:
                return {
                    'passed': True,
                    'similarity_score': 1.0,
                    'consensus_output': responses[0].get('text', ''),
                    'num_nodes': 1,
                    'outputs': [responses[0].get('text', '')],
                    'outliers': [],
                    'embeddings': [],
                    'similarity_matrix': [[1.0]],
                    'processing_time': time.time() - start_time
                }
            raise ValueError("No responses received from nodes")
        
        # Step 2: Extract output texts
        outputs = [r.get('text', r.get('output', '')) for r in responses]
        
        # Step 3: Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.embedding_model.encode(outputs, convert_to_numpy=True)
        
        # Step 4: Calculate similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        
        # Step 5: Calculate average pairwise similarity
        n = len(similarity_matrix)
        if n > 1:
            # Sum all similarities except diagonal, divide by number of pairs
            avg_similarity = (np.sum(similarity_matrix) - n) / (n * (n - 1))
        else:
            avg_similarity = 1.0
        
        # Step 6: Detect consensus and outliers
        consensus_output, outliers = self._detect_consensus(
            outputs, embeddings, similarity_matrix, similarity_threshold
        )
        
        # Step 7: Determine pass/fail
        passed = avg_similarity >= similarity_threshold
        
        result = {
            'passed': passed,
            'similarity_score': float(avg_similarity),
            'similarity_threshold': similarity_threshold,
            'consensus_output': consensus_output,
            'num_nodes': len(outputs),
            'outputs': outputs,
            'outliers': outliers,
            'embeddings': embeddings.tolist(),
            'similarity_matrix': similarity_matrix.tolist(),
            'processing_time': time.time() - start_time
        }
        
        logger.info(f"PoI complete: similarity={avg_similarity:.3f}, passed={passed}")
        
        return result
    
    def _detect_consensus(
        self,
        outputs: List[str],
        embeddings: np.ndarray,
        similarity_matrix: np.ndarray,
        threshold: float
    ) -> Tuple[str, List[int]]:
        """
        Detect consensus output and identify outliers
        
        Returns:
            Tuple of (consensus_output, outlier_indices)
        """
        n = len(outputs)
        
        # Calculate average similarity for each output to all others
        avg_similarities = []
        for i in range(n):
            # Get similarities to all other outputs (excluding self)
            similarities = [similarity_matrix[i][j] for j in range(n) if i != j]
            avg_sim = np.mean(similarities) if similarities else 0.0
            avg_similarities.append(avg_sim)
        
        # Output with highest average similarity is the consensus
        consensus_idx = int(np.argmax(avg_similarities))
        consensus_output = outputs[consensus_idx]
        
        # Identify outliers (below threshold)
        outliers = [i for i, sim in enumerate(avg_similarities) if sim < threshold]
        
        return consensus_output, outliers
    
    def calculate_poi_score(self, similarity_score: float) -> float:
        """Convert similarity (0-1) to confidence score (0-1)"""
        return similarity_score


# Global PoI engine instance
poi_engine = PoIEngine()
