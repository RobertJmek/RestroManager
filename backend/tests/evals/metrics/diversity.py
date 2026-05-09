"""
Diversity metrics for recommendation evaluation.

Intra-list diversity measures how different recommended items are from each other.
Higher diversity = more varied suggestions (better user exploration).
"""

from typing import List, Dict, Any, Set


def category_diversity(recommended_items: List[Dict[str, Any]]) -> int:
    """
    Count unique categories in recommendations.
    
    Args:
        recommended_items: List of recommended menu item dicts
        
    Returns:
        Number of unique categories
    """
    categories = set()
    for item in recommended_items:
        category = item.get("category") or item.get("cat", "")
        if category:
            categories.add(category)
    return len(categories)


def tag_diversity(recommended_items: List[Dict[str, Any]]) -> int:
    """
    Count unique dietary tags in recommendations.
    
    Args:
        recommended_items: List of recommended menu item dicts
        
    Returns:
        Number of unique dietary tags
    """
    all_tags = set()
    for item in recommended_items:
        tags = item.get("dietary_tags", [])
        if isinstance(tags, list):
            all_tags.update(tags)
    return len(all_tags)


def intra_list_diversity(recommended_ids: List[int], menu_lookup: Dict[int, Dict[str, Any]]) -> float:
    """
    Calculate intra-list diversity based on category dissimilarity.
    
    Higher score = more diverse (items from different categories)
    
    Args:
        recommended_ids: List of recommended item IDs
        menu_lookup: Dict mapping item_id -> menu item data
        
    Returns:
        Diversity score between 0 and 1
    """
    if len(recommended_ids) <= 1:
        return 1.0  # Single item is "perfectly diverse"
    
    # Get categories
    categories = []
    for item_id in recommended_ids:
        item = menu_lookup.get(item_id, {})
        cat = item.get("category", "unknown")
        categories.append(cat)
    
    # Calculate pairwise dissimilarity
    pairs = 0
    dissimilar = 0
    
    for i in range(len(categories)):
        for j in range(i + 1, len(categories)):
            pairs += 1
            if categories[i] != categories[j]:
                dissimilar += 1
    
    if pairs == 0:
        return 1.0
    
    return dissimilar / pairs


def price_diversity(recommended_items: List[Dict[str, Any]]) -> float:
    """
    Calculate coefficient of variation for prices (normalized std dev).
    
    Higher value = more price variety
    
    Args:
        recommended_items: List of recommended menu item dicts
        
    Returns:
        Price diversity score
    """
    prices = []
    for item in recommended_items:
        price = item.get("price", 0)
        if price > 0:
            prices.append(price)
    
    if len(prices) <= 1:
        return 0.0
    
    mean_price = sum(prices) / len(prices)
    if mean_price == 0:
        return 0.0
    
    variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
    std_dev = variance ** 0.5
    
    return std_dev / mean_price  # Coefficient of variation
