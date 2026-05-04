"""
ingestion.py - Baixa o dataset B2W-Reviews01 do HuggingFace e carrega no Supabase.
Também cria uma cópia local em data/raw/ para versionamento via DVC.
"""

import os
import pandas as pd
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configuração Supabase 
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Download do dataset 
PARQUET_URL = "https://huggingface.co/datasets/ruanchaves/b2w-reviews01/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
LOCAL_PATH = "data/raw/b2w_reviews_original.parquet"

os.makedirs("data/raw", exist_ok=True)

if not os.path.exists(LOCAL_PATH):
    print("Baixando B2W-Reviews01 do HuggingFace (Parquet)")
    response = requests.get(PARQUET_URL, stream=True)
    response.raise_for_status()
    with open(LOCAL_PATH, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Download concluído!")
else:
    print("Arquivo já existe localmente, pulando download.")

df = pd.read_parquet(LOCAL_PATH)
print(f"Total de registros: {len(df)}")
print(df.head(3))

# Seleciona e renomeia colunas relevantes
df = df[["review_text", "overall_rating", "recommend_to_a_friend"]].copy()
df = df.rename(columns={
    "review_text": "texto",
    "overall_rating": "nota",
    "recommend_to_a_friend": "recomenda"
})

# Cria coluna de sentimento com base na nota
# 1-2 estrelas → negativo | 3 → neutro | 4-5 → positivo
def mapear_sentimento(nota):
    if nota <= 2:
        return "negativo"
    elif nota == 3:
        return "neutro"
    else:
        return "positivo"

df["sentimento"] = df["nota"].apply(mapear_sentimento)
df = df.dropna(subset=["texto"])

print(f"\nDistribuição de sentimentos:\n{df['sentimento'].value_counts()}")

# Salva localmente para DVC
os.makedirs("data/raw", exist_ok=True)
df.to_csv("data/raw/b2w_reviews.csv", index=False)
print("\nSalvo em data/raw/b2w_reviews.csv")

# Carrega no Supabase (em lotes de 500) 
print("\nCarregando no Supabase...")
registros = df.to_dict(orient="records")
batch_size = 500

for i in range(0, len(registros), batch_size):
    lote = registros[i:i + batch_size]
    supabase.table("reviews").upsert(lote).execute()
    print(f"Lote {i // batch_size + 1} enviado ({len(lote)} registros)")

print("\nIngestão concluída!")