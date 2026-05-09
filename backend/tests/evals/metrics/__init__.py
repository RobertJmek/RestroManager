"""
Evaluation metrics for AI recommendation agent.

Provides:
- Precision@K, Recall@K, NDCG for recommendation quality
- Diversity metrics (intra-list diversity)
- Safety metrics (refusal rate, false positive rate)
"""

from .relevance import precision_at_k, recall_at_k, ndcg_at_k, calculate_relevance_scores
from .diversity import category_diversity, tag_diversity, intra_list_diversity
from .safety import refusal_rate, false_positive_rate, is_refusal, EXPECTED_REFUSAL

__all__ = [
    "precision_at_k",
    "recall_at_k", 
    "ndcg_at_k",
    "calculate_relevance_scores",
    "category_diversity",
    "tag_diversity",
    "intra_list_diversity",
    "refusal_rate",
    "false_positive_rate",
    "is_refusal",
    "EXPECTED_REFUSAL",
]
