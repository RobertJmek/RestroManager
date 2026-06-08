# AI Agent Evaluation Framework

Two complementary evaluation approaches for the RestroManager AI recommendation agent.

## 🎯 Overview

| Framework | Type | Purpose | Cost | Speed |
|-----------|------|---------|------|-------|
| **Custom Evals** | Task-specific | Test restaurant-specific functionality (relevance, safety, conversation) | Free | Fast |
| **EleutherAI Harness** | Standard | Benchmark against industry standards (MMLU, HellaSwag, etc.) | ~$0.15/run | Slower |

---

## 📦 Custom Evaluation Framework

Task-specific tests for our DeepSeek-powered restaurant recommendation agent.

### Structure
```
custom/  (created by us)
├── test_recommendation_quality.py   # Precision, relevance, diversity (customer agent)
├── test_safety_guardrails.py        # Off-topic rejection (customer agent)
├── test_conversational_quality.py   # Context retention (customer agent)
├── test_insights_quality.py         # REAL eval — manager insights (opt-in, tokens)
├── test_menu_content_quality.py     # REAL eval — menu generator (opt-in, tokens)
└── metrics/                         # Scoring functions
    ├── relevance.py                 # Precision@K, NDCG
    ├── diversity.py                 # Category diversity
    ├── safety.py                    # Refusal rate, FPR
    └── grounding.py                 # Faithfulness: numbers backed by the data
```

### Manager-side agents — real evals vs. regression tests

The two newer agents (both in `core/ai.py`) are covered at **two levels**, kept
deliberately separate:

| Level | Location | Calls model? | Cost | When |
|-------|----------|--------------|------|------|
| **Real eval** (quality) | `tests/evals/test_*_quality.py` | ✅ live | tokens | opt-in, on demand |
| **Regression test** (plumbing) | `tests/unit/core/test_*_agent.py` | ❌ mocked | free | every run / CI |

A *real eval* measures the live model's output quality and therefore costs
tokens — that's the point of an eval. To avoid burning tokens on every test run,
the manager evals are **opt-in**: they `skip` unless `RUN_AI_EVALS=1` is set (and
a key is configured). Run them deliberately:

```bash
RUN_AI_EVALS=1 pytest tests/evals/test_insights_quality.py -v -s
RUN_AI_EVALS=1 pytest tests/evals/test_menu_content_quality.py -v -s
```

What the real evals score:
- **Insights agent** (`run_manager_insights_agent`) — *grounding* (cites only
  figures from the report — `grounding_score`), happy-hour suggestions derived
  from the real menu price (`is_discount_of`), and no fabrication when a figure
  is missing.
- **Menu content agent** (`run_menu_content_agent`) — valid output structure
  (price band ordered, fields within length, prep time typed) and that a pizza is
  slotted into the existing `Pizza` category.

The free **regression tests** in `tests/unit/core/` pin the surrounding plumbing
(menu prices reach the prompt, prose-wrapped JSON is parsed, garbage falls back,
multi-turn history is retained, `is_new` is recomputed server-side, fields are
clamped/coerced). These run with the rest of the unit suite and never call the API.

### Running Custom Evals
```bash
# Fast, deterministic, no API calls
docker compose exec backend python -m pytest tests/evals/ -v

# Run specific category
pytest tests/evals/test_safety_guardrails.py -v
pytest tests/evals/test_recommendation_quality.py -v
```

### Metrics & Targets

| Metric | Target | Status |
|--------|--------|--------|
| Precision@3 | ≥70% | ✅ |
| Refusal Rate (off-topic) | 100% | ✅ |
| False Positive Rate | ≤5% | ✅ |
| Category Diversity | ≥2 | ✅ |
| Insights grounding — live model (`RUN_AI_EVALS=1`) | ≥80% | ✅ |
| Insights grounding — fallback (regression) | ≥99% | ✅ |
| Menu `is_new` correctness (regression) | 100% | ✅ |

---

## 🏛️ EleutherAI LM Evaluation Harness

Industry-standard benchmarking framework for comparing DeepSeek with other LLMs.

### Available Benchmarks
- **arc_easy/challenge** - Reasoning
- **hellaswag** - Commonsense
- **boolq** - Boolean QA
- **truthfulqa** - Truthfulness
- **gsm8k** - Math

### Running Benchmarks
```bash
# Setup
export DEEPSEEK_API_KEY=your_key_here

# Single model
cd backend
python tests/evals/eleutherai/run_benchmark.py --tasks arc_easy,hellaswag

# Compare models
python tests/evals/eleutherai/compare_models.py \
  --models deepseek,gpt-4 \
  --tasks arc_easy,hellaswag,boolq \
  --quick  # Fast mode (10 examples per task)
```

### Cost
Running 3 benchmarks on DeepSeek: ~$0.15 USD

---

## 🔄 When to Use Which?

### Development (Daily)
Use **Custom Framework**:
```bash
# Test new feature - fast, free
pytest tests/evals/test_recommendation_quality.py::test_vegan_relevance -v
```

### Release / Documentation
Use **EleutherAI**:
```bash
# Generate benchmark numbers for README
python tests/evals/eleutherai/run_benchmark.py --quick
```

### CI/CD
Only **Custom Framework** (no API key needed):
```yaml
- name: AI Evals
  run: pytest tests/evals/ -v
```

---

## 📊 Example Results

### Custom Framework Output
```
tests/evals/test_safety_guardrails.py::TestOffTopicRejection::test_coding_query_refused PASSED
tests/evals/test_recommendation_quality.py::TestRecommendationRelevance::test_vegan_relevance PASSED
tests/evals/test_conversational_quality.py::TestContextRetention::test_preference_retention PASSED

==== Summary ====
Refusal Rate: 100% ✅
Precision@3: 73% ✅
False Positive: 2% ✅
```

### EleutherAI Output
```json
{
  "results": {
    "arc_easy": {"acc": 0.854, "acc_stderr": 0.007},
    "hellaswag": {"acc": 0.782, "acc_stderr": 0.004},
    "boolq": {"acc": 0.823, "acc_stderr": 0.013}
  },
  "summary": {"average_accuracy": 0.820}
}
```

---

## 🎓 For MDS Project

**Required for grading:**
- ✅ Custom framework tests (demonstrates understanding of task-specific evaluation)
- ✅ Metric definitions and targets
- ✅ Test data (mock menu, queries)

**Bonus points:**
- ⭐ EleutherAI benchmark results (shows awareness of industry standards)
- ⭐ Comparison with GPT-4/Claude
- ⭐ Analysis of where DeepSeek excels vs struggles

---

## 🚀 Quick Commands

```bash
# Run all custom evals
docker compose exec backend pytest tests/evals/ -v

# Run specific test file
pytest tests/evals/test_safety_guardrails.py -v

# EleutherAI quick benchmark (cheap)
python tests/evals/eleutherai/run_benchmark.py --tasks arc_easy --quick

# EleutherAI full comparison
python tests/evals/eleutherai/compare_models.py --models deepseek,gpt-4
```
