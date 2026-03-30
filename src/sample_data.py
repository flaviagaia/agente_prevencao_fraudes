from __future__ import annotations

from pathlib import Path

import pandas as pd


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
TRANSACTIONS_PATH = RAW_DIR / "fraud_transactions.csv"


DEFAULT_TRANSACTIONS = [
    {
        "transaction_id": "FRD-1001",
        "customer_id": "CUS-9001",
        "event_ts": "2026-03-30T10:15:00",
        "amount_br": 12990,
        "merchant_category": "electronics",
        "payment_method": "credit_card",
        "device_change_24h": 0,
        "geo_distance_km": 8,
        "failed_attempts_24h": 1,
        "chargebacks_90d": 0,
        "account_age_days": 820,
        "velocity_1h": 2,
        "known_blacklist_match": 0,
        "email_risk_score": 0.08,
        "ip_risk_score": 0.12,
    },
    {
        "transaction_id": "FRD-1002",
        "customer_id": "CUS-9002",
        "event_ts": "2026-03-30T11:42:00",
        "amount_br": 48750,
        "merchant_category": "gift_cards",
        "payment_method": "credit_card",
        "device_change_24h": 1,
        "geo_distance_km": 1260,
        "failed_attempts_24h": 6,
        "chargebacks_90d": 2,
        "account_age_days": 34,
        "velocity_1h": 7,
        "known_blacklist_match": 1,
        "email_risk_score": 0.81,
        "ip_risk_score": 0.88,
    },
    {
        "transaction_id": "FRD-1003",
        "customer_id": "CUS-9003",
        "event_ts": "2026-03-30T14:08:00",
        "amount_br": 3490,
        "merchant_category": "groceries",
        "payment_method": "pix",
        "device_change_24h": 0,
        "geo_distance_km": 4,
        "failed_attempts_24h": 0,
        "chargebacks_90d": 0,
        "account_age_days": 560,
        "velocity_1h": 1,
        "known_blacklist_match": 0,
        "email_risk_score": 0.05,
        "ip_risk_score": 0.06,
    },
]


def ensure_sample_data() -> pd.DataFrame:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not TRANSACTIONS_PATH.exists():
        pd.DataFrame(DEFAULT_TRANSACTIONS).to_csv(TRANSACTIONS_PATH, index=False)
    return pd.read_csv(TRANSACTIONS_PATH)


def load_transactions() -> pd.DataFrame:
    return ensure_sample_data()


def load_transaction(transaction_id: str) -> dict:
    dataset = ensure_sample_data()
    match = dataset.loc[dataset["transaction_id"] == transaction_id]
    if match.empty:
        raise KeyError(f"Transaction id not found: {transaction_id}")
    return match.iloc[0].to_dict()
