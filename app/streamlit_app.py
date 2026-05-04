"""
streamlit_app.py
----------------
Interface principal — integra busca de hype no TikTok
com análise de sentimento dos comentários.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.predict import prever_sentimento

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="TikTok Trend Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 TikTok Trend Analyzer")
st.caption("Descubra o hype e o sentimento dos comentários de qualquer produto ou termo")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 Configurações")
    termo = st.text_input("Termo de busca", placeholder="ex: protetor solar, whey protein")
    dias  = st.slider("Período de análise (dias)", 7, 90, 30)
    botao = st.button("🚀 Analisar", type="primary", use_container_width=True)

    st.divider()
    st.caption("Pipeline: TikTok API → Supabase → DuckDB → ML → Streamlit")

# ── Função simulada de busca TikTok (substitua pela sua integração real) ──────
def buscar_dados_tiktok(termo: str, dias: int) -> pd.DataFrame:
    """
    TODO: substitua esta função pela sua integração real com a API do TikTok.
    Aqui retorna dados de exemplo para o pipeline funcionar end-to-end.
    """
    import random
    import numpy as np

    random.seed(hash(termo) % 1000)
    datas = pd.date_range(end=datetime.today(), periods=dias, freq="D")

    comentarios_exemplo = [
        f"Esse {termo} é incrível, amei muito!",
        f"Comprei o {termo} e não me arrependi",
        f"O {termo} chegou rápido e funciona bem",
        f"Não gostei do {termo}, veio com defeito",
        f"O {termo} é mais ou menos, esperava mais",
        f"Melhor {termo} que já comprei na vida!",
        f"Cuidado com esse {termo}, péssima qualidade",
        f"O {termo} tá em todo TikTok, testei e aprovei",
    ]

    registros = []
    for data in datas:
        n = random.randint(3, 15)
        for _ in range(n):
            registros.append({
                "data":       data,
                "comentario": random.choice(comentarios_exemplo),
                "likes":      random.randint(10, 5000),
                "views":      random.randint(1000, 500000),
            })

    return pd.DataFrame(registros)

# ── Main ──────────────────────────────────────────────────────────────────────
if botao and termo:
    with st.spinner(f'Buscando dados para "{termo}"...'):
        df = buscar_dados_tiktok(termo, dias)

    with st.spinner("Analisando sentimentos com IA..."):
        resultados = prever_sentimento(df["comentario"].tolist())
        df["sentimento"]  = [r["sentimento"]  for r in resultados]
        df["confianca"]   = [r["confianca"]   for r in resultados]
        df["prob_pos"]    = [r["probabilidades"].get("positivo", 0) for r in resultados]
        df["prob_neg"]    = [r["probabilidades"].get("negativo", 0) for r in resultados]
        df["prob_neu"]    = [r["probabilidades"].get("neutro",   0) for r in resultados]

    # ── Métricas principais ───────────────────────────────────────────────────
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    total       = len(df)
    pct_pos     = (df["sentimento"] == "positivo").mean()
    pct_neg     = (df["sentimento"] == "negativo").mean()
    total_views = df["views"].sum()

    col1.metric("💬 Comentários analisados", f"{total:,}")
    col2.metric("✅ Sentimento positivo",     f"{pct_pos:.0%}")
    col3.metric("❌ Sentimento negativo",     f"{pct_neg:.0%}")
    col4.metric("👁️ Views totais",            f"{total_views:,.0f}")

    st.divider()

    # ── Gráfico: evolução do sentimento ao longo do tempo ─────────────────────
    st.subheader("📈 Evolução do sentimento ao longo do tempo")

    evolucao = (
        df.groupby(["data", "sentimento"])
          .size()
          .reset_index(name="count")
    )

    cores = {
        "positivo": "#2ecc71",
        "neutro":   "#f39c12",
        "negativo": "#e74c3c"
    }

    fig_linha = px.line(
        evolucao,
        x="data", y="count", color="sentimento",
        color_discrete_map=cores,
        labels={"data": "Data", "count": "Comentários", "sentimento": "Sentimento"},
    )
    fig_linha.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend_title_text=""
    )
    st.plotly_chart(fig_linha, use_container_width=True)

    # ── Gráfico: distribuição de sentimentos ──────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🥧 Distribuição de sentimentos")
        dist = df["sentimento"].value_counts().reset_index()
        dist.columns = ["sentimento", "count"]
        fig_pizza = px.pie(
            dist, names="sentimento", values="count",
            color="sentimento", color_discrete_map=cores,
            hole=0.4
        )
        fig_pizza.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=True
        )
        st.plotly_chart(fig_pizza, use_container_width=True)

    with col_b:
        st.subheader("🔥 Hype Score por dia")
        hype = (
            df.groupby("data")
              .agg(views=("views","sum"), likes=("likes","sum"))
              .reset_index()
        )
        hype["hype_score"] = (
            (hype["views"] / hype["views"].max()) * 0.7 +
            (hype["likes"] / hype["likes"].max()) * 0.3
        ).round(3)

        fig_hype = px.bar(
            hype, x="data", y="hype_score",
            color="hype_score",
            color_continuous_scale=["#3498db", "#e74c3c"],
            labels={"data": "Data", "hype_score": "Hype Score"}
        )
        fig_hype.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_hype, use_container_width=True)

    # ── Tabela de comentários ─────────────────────────────────────────────────
    st.divider()
    st.subheader("💬 Comentários recentes")

    filtro = st.selectbox(
        "Filtrar por sentimento",
        ["todos", "positivo", "neutro", "negativo"]
    )

    df_exibir = df if filtro == "todos" else df[df["sentimento"] == filtro]

    def colorir(val):
        cores_bg = {"positivo": "#d5f5e3", "negativo": "#fde8e8", "neutro": "#fef9e7"}
        return f"background-color: {cores_bg.get(val, '')}"

    st.dataframe(
        df_exibir[["data", "comentario", "sentimento", "confianca", "likes", "views"]]
          .sort_values("data", ascending=False)
          .head(50)
          .style.applymap(colorir, subset=["sentimento"])
          .format({"confianca": "{:.0%}", "likes": "{:,.0f}", "views": "{:,.0f}"}),
        use_container_width=True,
        hide_index=True
    )

elif not botao:
    st.info("👈 Digite um termo na barra lateral e clique em **Analisar** para começar.")
