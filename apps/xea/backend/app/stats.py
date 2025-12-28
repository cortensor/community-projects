"""
Xea Governance Oracle - Statistical Utilities

Numerical helpers for aggregation: cosine distance, bootstrap confidence intervals,
and Mahalanobis distance outlier detection.
"""

import numpy as np
from typing import List, Tuple, Optional
import random


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    
    cosine_similarity(a, b) = (a · b) / (||a|| * ||b||)
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        Cosine similarity in range [-1, 1]
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(a, b) / (norm_a * norm_b))


def mean_pairwise_cosine_distance(embeddings: List[List[float]]) -> float:
    """
    Compute mean pairwise cosine distance across all embedding pairs.
    
    Cosine distance = 1 - cosine_similarity
    
    For n embeddings, we compute (n * (n-1)) / 2 pairwise distances
    and return their mean.
    
    Args:
        embeddings: List of embedding vectors (each is List[float])
        
    Returns:
        Mean pairwise cosine distance in range [0, 2]
        Returns 0.0 if fewer than 2 embeddings provided
        
    Reference:
        Cosine distance is commonly used for measuring semantic dispersion
        in embedding spaces. Lower values indicate higher agreement.
    """
    if len(embeddings) < 2:
        return 0.0
    
    # Convert to numpy arrays
    emb_arrays = [np.array(e) for e in embeddings]
    n = len(emb_arrays)
    
    distances = []
    for i in range(n):
        for j in range(i + 1, n):
            sim = cosine_similarity(emb_arrays[i], emb_arrays[j])
            distance = 1.0 - sim
            distances.append(distance)
    
    return float(np.mean(distances)) if distances else 0.0


def bootstrap_ci(
    values: List[float],
    n_iter: int = 1000,
    alpha: float = 0.05,
    seed: Optional[int] = None,
) -> Tuple[float, float]:
    """
    Compute bootstrap confidence interval for the mean.
    
    Bootstrap resampling procedure:
    1. Sample with replacement from values, n_iter times
    2. Compute the mean for each sample
    3. Return the (alpha/2, 1-alpha/2) percentiles
    
    Args:
        values: List of numeric values to bootstrap
        n_iter: Number of bootstrap iterations (default 1000)
        alpha: Significance level (default 0.05 for 95% CI)
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (lower_bound, upper_bound) for the CI
        
    Reference:
        Efron, B., & Tibshirani, R. J. (1993). An Introduction to the Bootstrap.
        Chapman & Hall/CRC.
        
    Example:
        >>> bootstrap_ci([0.8, 0.85, 0.9, 0.82, 0.88], n_iter=1000, alpha=0.05)
        (0.82, 0.88)  # Approximate 95% CI for the mean
    """
    if not values:
        return (0.0, 0.0)
    
    if len(values) == 1:
        return (values[0], values[0])
    
    if seed is not None:
        np.random.seed(seed)
    
    values_array = np.array(values)
    n = len(values_array)
    
    # Generate bootstrap means
    bootstrap_means = []
    for _ in range(n_iter):
        sample = np.random.choice(values_array, size=n, replace=True)
        bootstrap_means.append(np.mean(sample))
    
    # Compute percentiles
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100
    
    lower = float(np.percentile(bootstrap_means, lower_percentile))
    upper = float(np.percentile(bootstrap_means, upper_percentile))
    
    return (round(lower, 4), round(upper, 4))


def detect_mahalanobis_outliers(
    score_vectors: np.ndarray,
    threshold: float = 2.5,
) -> List[int]:
    """
    Detect outliers using Mahalanobis distance.
    
    The Mahalanobis distance measures how far a point is from the center
    of a distribution, accounting for correlations between variables.
    
    Formula:
        D² = (x - μ)ᵀ Σ⁻¹ (x - μ)
        
    Where:
        x = observation vector
        μ = mean vector
        Σ = covariance matrix
    
    Args:
        score_vectors: 2D numpy array of shape (n_samples, n_features)
                       Each row is a score vector [accuracy, omission_risk, 
                       evidence_quality, governance_relevance]
        threshold: Distance threshold for flagging outliers (default 2.5)
                   Lower threshold catches more outliers.
                   
    Returns:
        List of indices (0-based) of outlier observations
        
    Reference:
        Mahalanobis, P. C. (1936). On the generalized distance in statistics.
        Proceedings of the National Institute of Sciences of India.
        
    Note:
        If covariance matrix is singular (not invertible), we use the
        Moore-Penrose pseudo-inverse as a fallback.
    """
    if len(score_vectors) < 3:
        return []
    
    score_vectors = np.array(score_vectors, dtype=float)
    
    if score_vectors.ndim == 1:
        score_vectors = score_vectors.reshape(-1, 1)
    
    n_samples, n_features = score_vectors.shape
    
    if n_samples <= n_features:
        # Not enough samples for reliable covariance estimation
        # Fall back to simple z-score based detection
        mean = np.mean(score_vectors, axis=0)
        std = np.std(score_vectors, axis=0) + 1e-6
        z_scores = np.abs((score_vectors - mean) / std)
        max_z = np.max(z_scores, axis=1)
        return [i for i, z in enumerate(max_z) if z > 2.0]
    
    # Compute mean and covariance
    mean = np.mean(score_vectors, axis=0)
    cov = np.cov(score_vectors, rowvar=False)
    
    # Handle scalar covariance case
    if n_features == 1:
        cov = np.array([[cov]])
    
    # Compute inverse covariance (use pseudo-inverse for numerical stability)
    try:
        # Add small regularization for numerical stability
        cov_reg = cov + np.eye(n_features) * 1e-6
        inv_cov = np.linalg.inv(cov_reg)
    except np.linalg.LinAlgError:
        inv_cov = np.linalg.pinv(cov)
    
    # Compute Mahalanobis distance for each sample
    outliers = []
    distances = []
    for i, x in enumerate(score_vectors):
        diff = x - mean
        d_squared = diff @ inv_cov @ diff
        d = np.sqrt(max(0, d_squared))  # Ensure non-negative
        distances.append(d)
    
    # Use median + MAD based threshold for robustness
    distances = np.array(distances)
    median_d = np.median(distances)
    mad = np.median(np.abs(distances - median_d))
    
    # Threshold: points more than threshold * MAD from median
    if mad > 0:
        for i, d in enumerate(distances):
            if (d - median_d) / (mad + 1e-6) > threshold:
                outliers.append(i)
    else:
        # Fallback to simple threshold if MAD is 0
        for i, d in enumerate(distances):
            if d > threshold:
                outliers.append(i)
    
    return outliers


def compute_mode_agreement(verdicts: List[str]) -> Tuple[str, float]:
    """
    Compute the mode (most common) verdict and agreement ratio.
    
    Args:
        verdicts: List of verdict strings (e.g., ["verified", "verified", "refuted"])
        
    Returns:
        Tuple of (mode_verdict, agreement_ratio)
        agreement_ratio = count(mode) / len(verdicts)
    """
    if not verdicts:
        return ("unknown", 0.0)
    
    # Count occurrences
    counts = {}
    for v in verdicts:
        counts[v] = counts.get(v, 0) + 1
    
    # Find mode
    mode_verdict = max(counts, key=counts.get)
    mode_count = counts[mode_verdict]
    
    agreement = mode_count / len(verdicts)
    
    return (mode_verdict, round(agreement, 4))


def weighted_mean(values: List[float], weights: Optional[List[float]] = None) -> float:
    """
    Compute weighted mean of values.
    
    Args:
        values: List of numeric values
        weights: Optional list of weights (defaults to equal weights)
        
    Returns:
        Weighted mean
    """
    if not values:
        return 0.0
    
    if weights is None:
        return float(np.mean(values))
    
    values_arr = np.array(values)
    weights_arr = np.array(weights)
    
    # Normalize weights
    weights_arr = weights_arr / np.sum(weights_arr)
    
    return float(np.sum(values_arr * weights_arr))
