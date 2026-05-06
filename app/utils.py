import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from pytrends.request import TrendReq
from datetime import datetime, date, timedelta
import time
import base64
from dotenv import load_dotenv
load_dotenv()

# =======================================================
# FUNÇÕES DE BUSCA DE DADOS
# =======================================================

@st.cache_data(ttl=86400)
def fetch_tiktok_data(term):
    """
    Busca dados na API do TikTok com cache de 24 horas.

    :param term: O termo de pesquisa.
    :return: Lista de vídeos (dict) ou None se falhar.
    """
    try:
        API_KEY = os.getenv("TIKTOK_API_KEY")
        TIKTOK_HOST = os.getenv("TIKTOK_API_HOST")
    except Exception as e:
        st.error(f"ERRO: As chaves da API do TikTok não foram encontradas nos segredos. {e}")
        return None

    if not API_KEY or TIKTOK_HOST == "dummy_host" or API_KEY == "dummy_key":
        st.warning("Chaves da API do TikTok não configuradas. Pulando busca no TikTok.")
        return None

    url = f"https://{TIKTOK_HOST}/feed/search?keywords={term}&count=50"
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': TIKTOK_HOST
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()  # Levanta erro para status HTTP
        data = res.json()
        if data.get("code") == 0 and data.get("data", {}).get("videos"):
            return data["data"]["videos"]
        return []  # Retorna lista vazia se a API respondeu mas não há vídeos
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar à API do TikTok: {e}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao processar dados do TikTok: {e}")
        return None
 
@st.cache_data(ttl=86400) 
def fetch_tiktok_comments(video_url: str, count: int = 50) -> list[str]:
    try:
        API_KEY     = os.getenv("TIKTOK_API_KEY")
        TIKTOK_HOST = os.getenv("TIKTOK_API_HOST")
    except Exception as e:
        return []

    url = f"https://{TIKTOK_HOST}/comment/list"
    headers = {
        "x-rapidapi-key":  API_KEY,
        "x-rapidapi-host": TIKTOK_HOST
    }
    params = {
        "url":   video_url,
        "count": count
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        res.raise_for_status()
        data = res.json()
        comentarios = data.get("data", {}).get("comments", [])
        return [c.get("text", "") for c in comentarios if c.get("text")]
    except Exception as e:
        print(f"Erro comentários: {e}")
        return []
    
def fetch_comments_from_videos(videos: list[dict], max_videos: int = 5, comments_per_video: int = 30) -> list[str]:
    if not videos:
        return []

    sorted_videos = sorted(videos, key=lambda v: v.get("play_count", 0), reverse=True)
    top_videos = sorted_videos[:max_videos]

    print(f"Total de vídeos para buscar comentários: {len(top_videos)}")

    todos_comentarios = []
    for video in top_videos:
        video_id = video.get("video_id", "")  
        author   = video.get("author", {})
        username = author.get("unique_id", "") if isinstance(author, dict) else ""

        print(f"video_id: {video_id} | username: {username}")

        if video_id and username:
            video_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
            print(f"Buscando: {video_url}")
            comentarios = fetch_tiktok_comments(video_url, count=comments_per_video)
            print(f"Comentários retornados: {len(comentarios)}")
            todos_comentarios.extend(comentarios)

    return todos_comentarios


# =======================================================
# FUNÇÕES DE LÓGICA 
# =======================================================

def format_number(num):
    """
    Formata números grandes para K, M, B, ou arredonda números menores.

    :param num: O número (int ou float) a ser formatado.
    :return: String formatada.
    """
    if num >= 1_000_000_000:
        return f"{(num / 1_000_000_000):.1f}".replace('.0', '') + 'B'
    if num >= 1_000_000:
        return f"{(num / 1_000_000):.1f}".replace('.0', '') + 'M'
    if num >= 1_000:
        return f"{(num / 1_000):.1f}".replace('.0', '') + 'K'
    
    # Arredonda números menores que 1000 para o inteiro mais próximo
    return f"{num:.0f}"


def calculate_growth_metrics(df):
    """
    Calcula as métricas de média diária (14d vs 60d) para o IHP.
    Retorna também a contagem total de criadores únicos na amostra.

    :param df: DataFrame de vídeos do TikTok.
    :return: Dicionário com as métricas de média e contagem total, ou None se o df for inválido.
    """
    if df is None or df.empty or 'create_time' not in df.columns or 'play_count' not in df.columns:
        return None

    today = datetime.now()
    start_14d = today - timedelta(days=14)
    start_60d = today - timedelta(days=60)

    # Garante que create_time seja datetime
    df['create_time'] = pd.to_datetime(df['create_time'], errors='coerce')
    
    # Filtra removendo NaT (Not a Time) que podem ter surgido do coerce
    df_filtered = df.dropna(subset=['create_time'])

    df_14d = df_filtered[df_filtered['create_time'] >= start_14d]
    df_60d = df_filtered[df_filtered['create_time'] >= start_60d]
    
    # --- CÁLCULO DA DURAÇÃO REAL DA AMOSTRA ---
    
    # Calcula a duração REAL do período de 60 dias no dataset
    days_60d_range = 60.0
    if not df_60d.empty:
        min_date_60d = df_60d['create_time'].min()
        time_diff = today - min_date_60d
        days_60d_range = max(1.0, min(60.0, time_diff.total_seconds() / (24 * 3600)))
        
    # Calcula a duração REAL do período de 14 dias no dataset
    days_14d_range = 14.0
    if not df_14d.empty:
        min_date_14d = df_14d['create_time'].min()
        time_diff = today - min_date_14d
        days_14d_range = max(1.0, min(14.0, time_diff.total_seconds() / (24 * 3600)))
    
    # --- FIM DO CÁLCULO DA DURAÇÃO REAL ---


    # Somas
    views_sum_14d = df_14d['play_count'].sum()
    views_sum_60d = df_60d['play_count'].sum()
    likes_sum_14d = df_14d['digg_count'].sum() if 'digg_count' in df_14d.columns else 0
    likes_sum_60d = df_60d['digg_count'].sum() if 'digg_count' in df_60d.columns else 0
    comments_sum_14d = df_14d['comment_count'].sum() if 'comment_count' in df_14d.columns else 0
    comments_sum_60d = df_60d['comment_count'].sum() if 'comment_count' in df_60d.columns else 0
    shares_sum_14d = df_14d['share_count'].sum() if 'share_count' in df_14d.columns else 0
    shares_sum_60d = df_60d['share_count'].sum() if 'share_count' in df_60d.columns else 0

    # Contagem de Criadores Únicos
    # 1. Total de criadores únicos na AMOSTRA COMPLETA 
    total_unique_creators = 0
    if 'author_user_id' in df_filtered.columns:
        total_unique_creators = df_filtered.dropna(subset=['author_user_id'])['author_user_id'].nunique()
        
    # 2. Criadores Únicos no período (para o UCM momentum)
    unique_creators_14d = 0
    if 'author_user_id' in df_14d.columns:
        unique_creators_14d = df_14d.dropna(subset=['author_user_id'])['author_user_id'].nunique()

    unique_creators_60d = 0
    if 'author_user_id' in df_60d.columns:
        unique_creators_60d = df_60d.dropna(subset=['author_user_id'])['author_user_id'].nunique()


    # Médias diárias (Soma / N dias). 
    days_14d_norm = days_14d_range if days_14d_range >= 1.0 else 1.0
    days_60d_norm = days_60d_range if days_60d_range >= 1.0 else 1.0

    return {
        # Engajamento por Dia
        'views_14d_avg': views_sum_14d / days_14d_norm,
        'views_60d_avg': views_sum_60d / days_60d_norm,
        'likes_14d_avg': likes_sum_14d / days_14d_norm,
        'likes_60d_avg': likes_sum_60d / days_60d_norm,
        'comments_14d_avg': comments_sum_14d / days_14d_norm,
        'comments_60d_avg': comments_sum_60d / days_60d_norm,
        'shares_14d_avg': shares_sum_14d / days_14d_norm,
        'shares_60d_avg': shares_sum_60d / days_60d_norm,
        
        # Criadores Únicos por Dia (UCM Momentum)
        'creators_14d_avg': unique_creators_14d / days_14d_norm,
        'creators_60d_avg': unique_creators_60d / days_60d_norm,
        
        # Criadores Únicos na Amostra Total (para FD)
        'total_unique_creators': total_unique_creators,
        'total_videos_count': len(df_filtered) 
    }


def get_momentum_score(recent_avg, historical_avg):
    """
    Calcula o 'momentum' (0-200) comparando a média recente (14d)
    com a histórica (60d).

    :param recent_avg: Média dos últimos 14 dias.
    :param historical_avg: Média dos últimos 60 dias.
    :return: Pontuação de momentum (float) entre 0 e 200.
    """
    # Trata divisão por zero: se o histórico era 0 e o recente é > 0, é hype máximo.
    if historical_avg == 0 or pd.isna(historical_avg):
        return 200.0 if recent_avg > 0 else 0.0
    
    if pd.isna(recent_avg):
        recent_avg = 0.0

    ratio = recent_avg / historical_avg
    capped_ratio = min(ratio, 2.0)  # Limita em 2x (200%)
    score = capped_ratio * 100  # Escala para 0-200
    return score


def calculate_ihp(tiktok_metrics):
    """
    Calcula o Índice de Hype do TikTok (IHT) focado em Organicidade.

    Fórmula atualizada foca em:
    1. Momentum de Engajamento de Qualidade (Comentários e Shares)
    2. Fator de Distribuição (FD): Quantos criadores únicos existem na amostra vídeos.

    :param tiktok_metrics: Dicionário retornado por `calculate_growth_metrics`.
    :return: Dicionário com a pontuação IHT final e os scores de momentum.
    """
    # Pega os dados do TikTok. Se não existirem (None), usa 0.
    tm = tiktok_metrics or {}
    views_14d_avg = tm.get('views_14d_avg', 0)
    views_60d_avg = tm.get('views_60d_avg', 0)
    likes_14d_avg = tm.get('likes_14d_avg', 0)
    likes_60d_avg = tm.get('likes_60d_avg', 0)
    comments_14d_avg = tm.get('comments_14d_avg', 0)
    comments_60d_avg = tm.get('comments_60d_avg', 0)
    shares_14d_avg = tm.get('shares_14d_avg', 0)
    shares_60d_avg = tm.get('shares_60d_avg', 0)
    creators_14d_avg = tm.get('creators_14d_avg', 0)
    creators_60d_avg = tm.get('creators_60d_avg', 0)
    
    total_unique_creators = tm.get('total_unique_creators', 0)
    total_videos_count = tm.get('total_videos_count', 1) # Mínimo 1 para evitar divisão por zero

    # --- 1. CÁLCULO DO FATOR DE DISTRIBUIÇÃO (FD) ---
    # Pontuação de 0 a 100, baseado na proporção de criadores únicos na amostra de vídeos.
    # Ex: 50 criadores em 50 vídeos = FD de 100 (alta organicidade/pulverização)
    # Ex: 5 criadores em 50 vídeos = FD de 10 (baixa distribuição)
    distribution_ratio = total_unique_creators / total_videos_count
    FD_score = min(distribution_ratio * 100, 100) # Limita a 100

    # --- 2. CÁLCULO DO MOMENTUM SCORE ---
    # Momentum (14d vs 60d) para cada dimensão (0-200)
    V_m = get_momentum_score(views_14d_avg, views_60d_avg)
    L_m = get_momentum_score(likes_14d_avg, likes_60d_avg)
    C_m = get_momentum_score(comments_14d_avg, comments_60d_avg)
    S_m = get_momentum_score(shares_14d_avg, shares_60d_avg)
    UCM_m = get_momentum_score(creators_14d_avg, creators_60d_avg) # Momentum de Criadores/Dia

    # --- 3. FÓRMULA FINAL (PESO DE ORGANICIDADE) ---
    # Peso total = 100%. A pontuação máxima continua sendo 200 (se todos os momentos forem 200).
    # O Fator de Distribuição (FD) agora é uma métrica de base (0-100) que é ponderada.
    
    # Pesos (ajustados para 100%)
    ihp_total_momentum_score = (
        (C_m * 0.35) +    # Comentários: Engajamento de alta qualidade (35%)
        (S_m * 0.25) +    # Compartilhamentos: Prova de interesse forte (25%)
        (UCM_m * 0.15) +  # Momentum de Novos Criadores: Sinal de adoção crescente (15%)
        (L_m * 0.15) +    # Likes (15%)
        (V_m * 0.10)      # Views (10%)
    )
    
    # Combina o Momentum (14d vs 60d) com o Fator de Distribuição (FD).
    # O IHT é a média ponderada do Momentum Total e do FD.
    # Se o Momentum é alto (150) e a Distribuição é baixa (10), a média cai.
    # IHT (Escala 0-200, onde 100 é o ponto de equilíbrio, e 200 é o máximo teórico)
    ihp_total_score = (ihp_total_momentum_score * 0.70) + (FD_score * 0.30)
    ihp_total_score = min(ihp_total_score, 200) # Garante que não ultrapasse 200 


    return {
        'ihp_total_score': ihp_total_score,
        'views_momentum': V_m,
        'likes_momentum': L_m,
        'comments_momentum': C_m,
        'shares_momentum': S_m,
        'ucm_momentum': UCM_m,
        'fd_score': FD_score, 
    }


def get_ihp_recommendation(ihp_total_score):
    """
    Retorna uma string de recomendação baseada na pontuação IHP (0-200).

    :param ihp_total_score: A pontuação final do IHP.
    :return: Uma string de interpretação.
    """
    if ihp_total_score >= 150:
        return "Viral — tendência explosiva e orgânica"
    elif ihp_total_score >= 100:
        return "Em alta — hype crescendo com boa distribuição"
    elif ihp_total_score >= 60:
        return "Estável — atenção sustentada, monitorar distribuição"
    else:
        return "Interesse em queda — produto esfriando ou campanha concentrada"


# =======================================================
# ESTILOS CSS
# =======================================================

def load_css_styles(img_base64, tema_cor):
    return f"""
<style>
    [data-testid="stSidebar"] {{ display: none !important; }}
    #MainMenu, footer {{ visibility: hidden; }}
    
    /* CAPA  */
    .hype-cover {{
        position: relative;
        width: 100%;
        height: 220px;
        border-radius: 12px;
        background-image: url('data:image/png;base64,{img_base64}');
        background-size: cover;
        background-position: center;
        display: flex;
        align-items: center;
        justify-content: flex-start; 
        margin-bottom: 30px;
        padding-left: 5%;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }}
    .hype-cover::after {{
        content: "";
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        border-radius: 12px;
        background: rgba(0, 0, 0, 0.4); 
    }}
    .hype-cover h1 {{
        position: relative;
        color: "#E02E30";
        font-size: 2.5rem;
        font-weight: 800;
        text-align: left !important;
        z-index: 2;
        margin: 0;
    }}

    [data-testid="stMetric"] {{
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 12px; 
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
        height: 100%;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.9rem; 
        color: #555; 
        font-weight: 500;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 2.5rem; 
        font-weight: 700; 
        color: {tema_cor};
    }}

    .metric-card, .metric-card-trends {{
        background-color: #ffffff;
        border: 1px solid {tema_cor}; 
        border-radius: 12px; 
        padding: 18px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        height: 100%; 
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}

    .metric-card:hover, .metric-card-trends:hover {{
        transform: translateY(-4px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        border-color: {tema_cor};
    }}

    /* Valor principal do IHP */
    .metric-card .metric-value {{
        font-size: 28px;
        font-weight: 700;
        color: {tema_cor};
        margin-bottom: 6px;
    }}

    /* Labels */
    .metric-card .metric-label {{
        font-size: 13px;
        color: #555; 
    }}

    /* Valor dos cards de TikTok */
    .metric-card .metric-value-white {{
        font-size: 28px;
        font-weight: 700;
        color: {tema_cor};
        margin-bottom: 6px;
    }}

    /* Labels dos cards do Google Trends */
    .metric-card-trends .metric-label-trends {{
        font-size: 13px;
        color: #555;
        margin-bottom: 2px;
        font-weight: 500;
    }}

    /* Valores dos cards do Google Trends */
    .metric-card-trends .metric-value-trends {{
        font-size: 20px;
        font-weight: 700;
        color: {tema_cor}; 
    }}

    /* BLOCO DE RECOMENDAÇÃO (IHP) */
    .recommendation-box {{
        background-color: #ffffff;
        border: 1px solid #e0e0e0; /* Borda padronizada */
        border-radius: 12px; 
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
        height: 100%; 
    }}
    .recommendation-title {{
        font-size: 1.2rem;
        font-weight: 700;
        color: #222;
        margin-bottom: 10px;
        border-bottom: 2px solid {tema_cor}; 
        padding-bottom: 5px;
    }}
    .recommendation-text {{
        font-size: 1.1rem;
        font-weight: 600;
        color: {tema_cor}; 
        margin-bottom: 10px;
    }}

    /* TABELA DE MÉDIAS*/
    .thirtyd-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        font-size: 15px;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    .thirtyd-table thead th {{
        background-color: #f8f9fa; 
        color: #333; 
        font-weight: 600;
        text-align: right; 
        padding: 12px 15px;
        border-bottom: 2px solid #dee2e6; 
    }}
    .thirtyd-table thead th:first-child {{
        text-align: left;
    }}
    .thirtyd-table tbody td {{
        color: #555; 
        padding: 12px 15px;
        border-bottom: 1px solid #f0f0f0; 
        text-align: right; 
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 15px;
        background-color: #ffffff;
    }}
    .thirtyd-table tbody tr:last-child td {{
        border-bottom: none; 
    }}
    .thirtyd-table tbody tr:hover td {{
        background-color: #f9f9f9; 
    }}
    .thirtyd-table td:first-child {{
        font-weight: 600;
        color: #222; 
        text-align: left;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .ihp-container {{
        display: flex;
        flex-direction: column;
        height: 100%; 
        min-height: 200px; 
        justify-content: space-between; 
    }}
    .recommendation-box {{
        min-height: 200px;
    }}
    .ihp-container [data-testid="stAlert"] {{
        margin-top: 5px;
        margin-bottom: 0px;
        padding: 5px 10px;
    }}
    
    /* Classe de aviso personalizada */
    .warning-card {{
        background-color: #fff3cd;
        color: #856404;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #ffeeba;
        margin-top: 10px;
        font-size: 0.9rem;
    }}
</style>
"""