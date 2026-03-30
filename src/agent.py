from __future__ import annotations

import os
from typing import Any

from .tools import (
    build_evidence_path,
    build_fallback_report,
    classify_fraud_decision,
    compute_fraud_signals,
    explain_fraud_decision,
    get_transaction_context,
    lookup_historical_pattern,
)

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
except Exception:  # pragma: no cover - optional dependency
    vertexai = None
    GenerativeModel = None


def _build_vertex_model(model_name: str = "gemini-2.0-flash-001"):
    if not (vertexai and GenerativeModel and os.getenv("GOOGLE_CLOUD_PROJECT") and os.getenv("GOOGLE_CLOUD_LOCATION")):
        return None
    try:
        vertexai.init(project=os.getenv("GOOGLE_CLOUD_PROJECT"), location=os.getenv("GOOGLE_CLOUD_LOCATION"))
        return GenerativeModel(model_name)
    except Exception:
        return None


def ask_fraud_prevention_agent(
    transaction_id: str,
    user_question: str,
    model_name: str = "gemini-2.0-flash-001",
) -> dict[str, Any]:
    report = build_fallback_report(transaction_id=transaction_id, user_question=user_question)
    model = _build_vertex_model(model_name=model_name)
    if model is None:
        return {"runtime_mode": "deterministic_fallback", **report}

    prompt = (
        f"transaction_id={transaction_id}\n"
        f"user_question={user_question}\n"
        f"context={get_transaction_context(transaction_id)}\n"
        f"fraud_signals={compute_fraud_signals(transaction_id)}\n"
        f"historical_pattern={lookup_historical_pattern(transaction_id)}\n"
        f"classification={classify_fraud_decision(transaction_id)}\n"
        f"evidence_path={build_evidence_path(transaction_id)}\n"
        "Explain the fraud risk decision in a concise analyst-friendly way without inventing data."
    )
    try:
        response = model.generate_content(prompt)
        text = getattr(response, "text", "") or report["final_message"]
        report["final_message"] = text
        return {"runtime_mode": "gcp_vertex_agent", **report}
    except Exception:
        return {"runtime_mode": "deterministic_fallback", **report}
