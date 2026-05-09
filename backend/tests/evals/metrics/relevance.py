"""
Relevance metrics for recommendation quality evaluation.

Precision@K: Ratio of relevant items in top-K suggestions
Recall@K: Ratio of all relevant items covered in top-K
NDCG@K: Normalized Discounted Cumulative Gain (ranking quality)
"""

from typing import List, Set, Dict, Any


def precision_at_k(recommended: List[int], relevant: Set[int], k: int = 3) -> float:
    """
    Calculate Precision@K.
    
    Args:
        recommended: List of item IDs in recommendation order
        relevant: Set of item IDs that are relevant to the query
        k: Number of top items to consider
        
    Returns:
        Precision score between 0 and 1
    """
    if not recommended or k <= 0:
        return 0.0
    
    top_k = recommended[:k]
    relevant_in_k = sum(1 for item in top_k if item in relevant)
    return relevant_in_k / len(top_k)


def recall_at_k(recommended: List[int], relevant: Set[int], k: int = 10) -> float:
    """
    Calculate Recall@K.
    
    Args:
        recommended: List of item IDs in recommendation order
        relevant: Set of item IDs that are relevant to the query
        k: Number of top items to consider
        
    Returns:
        Recall score between 0 and 1
    """
    if not relevant:
        return 1.0  # Nothing to recall
    
    if not recommended:
        return 0.0
    
    top_k = recommended[:k]
    relevant_in_k = sum(1 for item in top_k if item in relevant)
    return relevant_in_k / len(relevant)


def dcg_at_k(relevances: List[float], k: int) -> float:
    """
    Calculate DCG@K (Discounted Cumulative Gain).
    
    Args:
        relevances: List of relevance scores in ranking order
        k: Number of top items to consider
        
    Returns:
        DCG score
    """
    import math
    
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        # Position i+1 (1-indexed)
        position = i + 1
        dcg += rel / math.log2(position + 1)
    return dcg


def ndcg_at_k(recommended: List[int], relevance_map: Dict[int, float], k: int = 3) -> float:
    """
    Calculate NDCG@K (Normalized DCG).
    
    Args:
        recommended: List of item IDs in recommendation order
        relevance_map: Dict mapping item_id -> relevance score (0-1)
        k: Number of top items to consider
        
    Returns:
        NDCG score between 0 and 1
    """
    if not recommended or not relevance_map:
        return 0.0
    
    # Get relevance scores for recommended items
    relevances = [relevance_map.get(item, 0.0) for item in recommended[:k]]
    
    # Calculate DCG
    dcg = dcg_at_k(relevances, k)
    
    # Calculate ideal DCG (perfect ranking)
    ideal_relevances = sorted(relevance_map.values(), reverse=True)[:k]
    idcg = dcg_at_k(ideal_relevances, k)
    
    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def calculate_relevance_scores(
    recommended_items: List[Dict[str, Any]],
    expected_tags: List[str],
    expected_categories: List[str],
    menu_lookup: Dict[int, Dict[str, Any]]
) -> Dict[int, float]:
    """
    Calculate relevance scores for items based on tag/category matching.
    
    Returns dict mapping item_id -> relevance_score (0-1)
    """
    relevance_map = {}
    
    for item_id, menu_item in menu_lookup.items():
        score = 0.0
        item_tags = set(menu_item.get("dietary_tags", []))
        item_category = menu_item.get("category", "")
        
        # Score based on tag matches
        if expected_tags:
            matching_tags = item_tags & set(expected_tags)
            score += len(matching_tags) / len(expected_tags) * 0.7
        
        # Score based on category matches
        if expected_categories:
            if item_category in expected_categories:
                score += 0.3
        
        relevance_map[item_id] = min(score, 1.0)
    
    return relevance_map
