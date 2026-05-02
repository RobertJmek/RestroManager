from typing import List

def run_ai_kds_optimizer(items: List[dict]) -> str:
    """
    AGENT AI 1: Kitchen Optimizer. 
    Analizează complexitatea produselor pentru a sugera prioritizarea.
    """
    total_prep_expected = sum([item.get("prep_time", 10) for item in items])
    if total_prep_expected > 25:
        return "HIGH_COMPLEXITY - Start Prep Immediately"
    return "STANDARD_PRIORITY"

def run_ai_safety_agent(notes: str) -> str:
    """
    AGENT AI 2: Safety & Urgency Agent.
    Detectează riscuri de sănătate sau solicitări urgente.
    """
    keywords = ["alergie", "allergy", "urgent", "copil", "baby"]
    if any(word in notes.lower() for word in keywords):
        return "CRITICAL"
    return "NORMAL"
