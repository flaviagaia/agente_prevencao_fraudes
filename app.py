from __future__ import annotations

import streamlit as st

from src.agent import ask_fraud_prevention_agent
from src.sample_data import load_transactions


st.set_page_config(page_title="Agente de Prevencao a Fraudes", layout="wide")
st.title("Agente de Prevencao a Fraudes")
st.caption("MVP com ferramentas GCP para sinais de fraude, lookup histórico e trilha de evidência.")

transactions = load_transactions()
options = transactions.set_index("transaction_id")["customer_id"].to_dict()

with st.sidebar:
    st.header("Ferramentas GCP")
    st.markdown(
        """
        - `BigQuery` para lookup histórico de padrões similares
        - `Cloud Storage` para trilha de evidências
        - `Vertex AI Gemini` para explicação final opcional
        - fallback local para execução sem credenciais
        """
    )
    st.header("Objetivo do MVP")
    st.markdown(
        """
        - detectar sinais relevantes de fraude
        - combinar risco transacional e histórico
        - propor decisão de approve/review/block
        - expor trilha de evidência e explicação
        """
    )

transaction_id = st.selectbox(
    "Selecione a transação",
    options=list(options.keys()),
    format_func=lambda tid: f"{tid} - {options[tid]}",
)

question = st.text_area(
    "Pergunta analítica",
    value="Essa transação deveria ser aprovada, revisada ou bloqueada?",
    height=120,
)

if st.button("Executar agente", type="primary"):
    result = ask_fraud_prevention_agent(transaction_id=transaction_id, user_question=question)

    c1, c2, c3 = st.columns(3)
    c1.metric("Runtime mode", result["runtime_mode"])
    c2.metric("Decisão", result["classification"]["decision"])
    c3.metric("Banda de risco", result["classification"]["fraud_risk_band"])

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Mensagem final", "Sinais e histórico", "Classificação e evidências", "Transação consultada"]
    )
    with tab1:
        st.markdown(result["final_message"])
    with tab2:
        st.write(result["decision_explanation"])
        st.json(result["fraud_signals"])
        st.json(result["historical_pattern"])
    with tab3:
        st.json(result["classification"])
        st.json(result["evidence_path"])
    with tab4:
        st.json(result["transaction"])

st.divider()
st.subheader("Arquitetura resumida")
st.code(
    """Analista -> ferramentas GCP (BigQuery, GCS, Vertex AI) -> decisão de fraude + evidências
          \\-> fallback determinístico local (sem credenciais GCP)""",
    language="text",
)
