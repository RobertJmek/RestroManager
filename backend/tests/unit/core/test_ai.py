import pytest
from core.ai import run_ai_kds_optimizer, run_ai_safety_agent

def test_run_ai_kds_optimizer_high_complexity():
    items = [{"prep_time": 15}, {"prep_time": 15}]
    result = run_ai_kds_optimizer(items)
    assert result == "HIGH_COMPLEXITY - Start Prep Immediately"

def test_run_ai_kds_optimizer_standard():
    items = [{"prep_time": 10}, {"prep_time": 10}]
    result = run_ai_kds_optimizer(items)
    assert result == "STANDARD_PRIORITY"

def test_run_ai_safety_agent_critical():
    notes = "Fara alune, are alergie severa"
    result = run_ai_safety_agent(notes)
    assert result == "CRITICAL"

def test_run_ai_safety_agent_normal():
    notes = "Vreau mai mult sos"
    result = run_ai_safety_agent(notes)
    assert result == "NORMAL"
