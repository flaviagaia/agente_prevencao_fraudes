from __future__ import annotations

import json
import os
from typing import Any

from .sample_data import load_transaction, load_transactions

try:
    from google.cloud import bigquery
    from google.cloud import storage
except Exception:  # pragma: no cover - optional dependencies
    bigquery = None
    storage = None


def get_transaction_context(transaction_id: str) -> dict[str, Any]:
    """Retorna o snapshot canônico da transação sob análise."""
    return load_transaction(transaction_id)


def compute_fraud_signals(transaction_id: str) -> dict[str, Any]:
    """Calcula sinais heurísticos de fraude a partir do evento."""
    tx = load_transaction(transaction_id)
    risk_flags: list[str] = []

    if float(tx["geo_distance_km"]) >= 500:
        risk_flags.append("anomalia_geografica")
    if int(tx["failed_attempts_24h"]) >= 5:
        risk_flags.append("muitas_tentativas_falhas")
    if int(tx["chargebacks_90d"]) >= 1:
        risk_flags.append("historico_chargeback")
    if int(tx["velocity_1h"]) >= 5:
        risk_flags.append("alta_velocidade_transacional")
    if int(tx["device_change_24h"]) == 1:
        risk_flags.append("mudanca_recente_de_dispositivo")
    if int(tx["known_blacklist_match"]) == 1:
        risk_flags.append("match_em_blacklist")
    if float(tx["email_risk_score"]) >= 0.7:
        risk_flags.append("email_risco_alto")
    if float(tx["ip_risk_score"]) >= 0.7:
        risk_flags.append("ip_risco_alto")

    merchant_risk = "alto" if str(tx["merchant_category"]) in {"gift_cards", "crypto", "electronics"} else "moderado"

    return {
        "transaction_id": transaction_id,
        "risk_flags": risk_flags,
        "merchant_risk": merchant_risk,
        "failed_attempts_24h": int(tx["failed_attempts_24h"]),
        "chargebacks_90d": int(tx["chargebacks_90d"]),
    }


def lookup_historical_pattern(transaction_id: str) -> dict[str, Any]:
    """Consulta histórico similar. Usa BigQuery quando configurado, senão fallback local."""
    tx = load_transaction(transaction_id)

    if bigquery and os.getenv("GOOGLE_CLOUD_PROJECT") and os.getenv("FRAUD_BIGQUERY_TABLE"):
        try:
            client = bigquery.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
            query = f"""
                SELECT COUNT(*) AS similar_events,
                       AVG(CAST(chargebacks_90d > 0 AS INT64)) AS chargeback_rate
                FROM `{os.getenv("FRAUD_BIGQUERY_TABLE")}`
                WHERE merchant_category = @merchant_category
                  AND payment_method = @payment_method
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("merchant_category", "STRING", tx["merchant_category"]),
                    bigquery.ScalarQueryParameter("payment_method", "STRING", tx["payment_method"]),
                ]
            )
            rows = list(client.query(query, job_config=job_config).result())
            if rows:
                return {
                    "source": "bigquery",
                    "similar_events": int(rows[0]["similar_events"] or 0),
                    "chargeback_rate": round(float(rows[0]["chargeback_rate"] or 0), 4),
                }
        except Exception:
            pass

    dataset = load_transactions()
    similar = dataset[
        (dataset["merchant_category"] == tx["merchant_category"])
        & (dataset["payment_method"] == tx["payment_method"])
    ]
    chargeback_rate = round((similar["chargebacks_90d"] > 0).mean() if len(similar) else 0.0, 4)
    return {
        "source": "local_fallback",
        "similar_events": int(len(similar)),
        "chargeback_rate": chargeback_rate,
    }


def build_evidence_path(transaction_id: str) -> dict[str, Any]:
    """Monta a trilha de evidência. Usa Cloud Storage quando configurado."""
    if storage and os.getenv("GCS_FRAUD_BUCKET"):
        try:
            client = storage.Client()
            bucket = client.bucket(os.getenv("GCS_FRAUD_BUCKET"))
            blob = bucket.blob(f"fraud-evidence/{transaction_id}.json")
            return {
                "source": "gcs",
                "artifact_uri": f"gs://{bucket.name}/{blob.name}",
            }
        except Exception:
            pass

    return {
        "source": "local_fallback",
        "artifact_uri": f"data/processed/{transaction_id}_evidence.json",
    }


def classify_fraud_decision(transaction_id: str) -> dict[str, Any]:
    """Classifica a transação em approve/review/block."""
    signals = compute_fraud_signals(transaction_id)
    history = lookup_historical_pattern(transaction_id)
    score = 0
    score += 3 if "match_em_blacklist" in signals["risk_flags"] else 0
    score += 2 if "anomalia_geografica" in signals["risk_flags"] else 0
    score += 2 if "muitas_tentativas_falhas" in signals["risk_flags"] else 0
    score += 2 if "historico_chargeback" in signals["risk_flags"] else 0
    score += 1 if "alta_velocidade_transacional" in signals["risk_flags"] else 0
    score += 1 if "mudanca_recente_de_dispositivo" in signals["risk_flags"] else 0
    score += 1 if history["chargeback_rate"] >= 0.3 else 0

    if score >= 7:
        decision = "block"
        band = "alto"
    elif score >= 3:
        decision = "review"
        band = "moderado"
    else:
        decision = "approve"
        band = "baixo"

    return {
        "transaction_id": transaction_id,
        "decision": decision,
        "fraud_risk_band": band,
        "fraud_score": score,
    }


def explain_fraud_decision(transaction_id: str) -> str:
    """Gera racional executivo grounded na transação."""
    tx = load_transaction(transaction_id)
    signals = compute_fraud_signals(transaction_id)
    history = lookup_historical_pattern(transaction_id)
    classification = classify_fraud_decision(transaction_id)
    flags = ", ".join(signals["risk_flags"]) if signals["risk_flags"] else "sem alertas críticos"

    return (
        f"A transação {transaction_id} de {tx['customer_id']} foi classificada com risco {classification['fraud_risk_band']} "
        f"e decisão sugerida `{classification['decision']}`. Sinais observados: {flags}. "
        f"O padrão histórico similar indica chargeback_rate de {history['chargeback_rate']:.1%}."
    )


def build_fallback_report(transaction_id: str, user_question: str) -> dict[str, Any]:
    tx = get_transaction_context(transaction_id)
    signals = compute_fraud_signals(transaction_id)
    history = lookup_historical_pattern(transaction_id)
    evidence = build_evidence_path(transaction_id)
    classification = classify_fraud_decision(transaction_id)
    explanation = explain_fraud_decision(transaction_id)

    final_message = (
        f"Pergunta analítica: {user_question}\n\n"
        f"Transação consultada:\n{json.dumps(tx, ensure_ascii=False, indent=2)}\n\n"
        f"Sinais de fraude:\n{json.dumps(signals, ensure_ascii=False, indent=2)}\n\n"
        f"Histórico similar:\n{json.dumps(history, ensure_ascii=False, indent=2)}\n\n"
        f"Trilha de evidência:\n{json.dumps(evidence, ensure_ascii=False, indent=2)}\n\n"
        f"Classificação:\n{json.dumps(classification, ensure_ascii=False, indent=2)}\n\n"
        f"Explicação:\n{explanation}"
    )

    return {
        "transaction_id": transaction_id,
        "transaction": tx,
        "fraud_signals": signals,
        "historical_pattern": history,
        "evidence_path": evidence,
        "classification": classification,
        "decision_explanation": explanation,
        "final_message": final_message,
    }
