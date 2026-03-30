from __future__ import annotations

import unittest

from src.agent import ask_fraud_prevention_agent
from src.sample_data import ensure_sample_data
from src.tools import classify_fraud_decision, compute_fraud_signals


class FraudPreventionAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        ensure_sample_data()

    def test_signals_return_flags(self) -> None:
        signals = compute_fraud_signals("FRD-1002")
        self.assertGreaterEqual(len(signals["risk_flags"]), 1)
        self.assertIn("match_em_blacklist", signals["risk_flags"])

    def test_classification_returns_decision(self) -> None:
        decision = classify_fraud_decision("FRD-1001")
        self.assertIn(decision["decision"], {"approve", "review", "block"})

    def test_agent_returns_final_message(self) -> None:
        result = ask_fraud_prevention_agent(
            transaction_id="FRD-1003",
            user_question="Há sinais materiais de fraude nessa transação?",
        )
        self.assertIn("runtime_mode", result)
        self.assertIn("final_message", result)
        self.assertIn("classification", result)


if __name__ == "__main__":
    unittest.main()
