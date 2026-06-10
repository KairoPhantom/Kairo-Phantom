#!/usr/bin/env python3
"""
tests/routing_test.py — Model Router Tiering tests
===================================================
"""

import sys
import os

# Add sidecar directory to path to import model_router
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kairo-sidecar"))

from sidecar.model_router import (
    select_model, model_tier_label,
    MODEL_FAST, MODEL_STANDARD, MODEL_THINK, MODEL_CLOUD
)

def run_tests():
    test_cases = [
        # 1. select_model(task_type='insert', confidence=0.9, estimated_tokens=50) == MODEL_FAST
        {
            "args": {"task_type": "insert", "confidence": 0.9, "estimated_tokens": 50},
            "expected": MODEL_FAST
        },
        # 2. select_model(task_type='insert', confidence=0.6, estimated_tokens=50) == MODEL_STANDARD
        {
            "args": {"task_type": "insert", "confidence": 0.6, "estimated_tokens": 50},
            "expected": MODEL_STANDARD
        },
        # 3. select_model(task_type='analyze', confidence=0.85, estimated_tokens=300) == MODEL_STANDARD
        {
            "args": {"task_type": "analyze", "confidence": 0.85, "estimated_tokens": 300},
            "expected": MODEL_STANDARD
        },
        # 4. select_model(waza_agent='legal_reviewer', estimated_tokens=600) == MODEL_THINK
        {
            "args": {"waza_agent": "legal_reviewer", "estimated_tokens": 600},
            "expected": MODEL_THINK
        },
        # 5. select_model(waza_agent='medical_scribe', estimated_tokens=100) == MODEL_THINK
        {
            "args": {"waza_agent": "medical_scribe", "estimated_tokens": 100},
            "expected": MODEL_THINK
        },
        # 6. select_model(requires_web_search=True) == MODEL_CLOUD
        {
            "args": {"requires_web_search": True},
            "expected": MODEL_CLOUD
        },
        # 7. select_model(estimated_tokens=2000) == MODEL_CLOUD
        {
            "args": {"estimated_tokens": 2000},
            "expected": MODEL_CLOUD
        },
        # 8. select_model(task_type='replace', confidence=0.9, estimated_tokens=100) == MODEL_FAST
        {
            "args": {"task_type": "replace", "confidence": 0.9, "estimated_tokens": 100},
            "expected": MODEL_FAST
        },
        # 9. select_model(task_type='replace', confidence=0.9, estimated_tokens=200) == MODEL_STANDARD
        {
            "args": {"task_type": "replace", "confidence": 0.9, "estimated_tokens": 200},
            "expected": MODEL_STANDARD
        },
        # 10. select_model(force_tier='kairo-think') == MODEL_THINK
        {
            "args": {"force_tier": "kairo-think"},
            "expected": MODEL_THINK
        }
    ]

    failed = 0
    for idx, tc in enumerate(test_cases, 1):
        res = select_model(**tc["args"])
        if res == tc["expected"]:
            print(f"Test {idx}: PASS (args={tc['args']} -> {res})")
        else:
            print(f"Test {idx}: FAIL (args={tc['args']} -> got {res}, expected {tc['expected']})")
            failed += 1

    # Check model_tier_label
    for tier in [MODEL_FAST, MODEL_STANDARD, MODEL_THINK, MODEL_CLOUD]:
        label = model_tier_label(tier)
        if not label:
            print(f"Label Test for '{tier}': FAIL (empty)")
            failed += 1
        else:
            print(f"Label Test for '{tier}': PASS ({label})")

    if failed == 0:
        print("\nALL ROUTING TESTS PASSED")
        sys.exit(0)
    else:
        print(f"\n{failed} ROUTING TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
