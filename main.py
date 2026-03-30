from __future__ import annotations

import json
from pathlib import Path

from src.agent import ask_fraud_prevention_agent
from src.sample_data import ensure_sample_data


def main() -> None:
    ensure_sample_data()
    result = ask_fraud_prevention_agent(
        transaction_id="FRD-1002",
        user_question="Essa transação deveria ser bloqueada ou apenas revisada manualmente?",
    )
    output_path = Path(__file__).resolve().parent / "data" / "processed" / "fraud_prevention_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Agente Prevencao Fraudes")
    print(f"runtime_mode: {result['runtime_mode']}")
    print(f"transaction_id: {result['transaction_id']}")
    print(f"decision: {result['classification']['decision']}")
    print(f"fraud_risk_band: {result['classification']['fraud_risk_band']}")
    print(f"output_path: {output_path}")


if __name__ == "__main__":
    main()
