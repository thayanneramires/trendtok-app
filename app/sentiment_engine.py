
import pickle
import pandas as pd
from pathlib import Path

MODEL_PATH = Path("data/models/modelo_sentimento.pkl")

def analyze_video_sentiments(df_videos):
    """
    Carrega o modelo e analisa a coluna 'desc' (ou comentários se disponíveis).
    """
    if df_videos.empty:
        return df_videos

    # Carrega o modelo treinado
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    # Predição direta no DataFrame
    df_videos['sentiment'] = model.predict(df_videos['desc'].fillna(""))
    
    return df_videos