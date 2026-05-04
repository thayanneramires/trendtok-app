"""
preprocessing.py
----------------
1. Puxa os dados do Supabase para um DataFrame
2. Registra o DataFrame no DuckDB como tabela em memória
3. Aplica limpeza e feature engineering via SQL
4. Salva o resultado em data/processed/ como Parquet
"""

import os
import re
import duckdb
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Puxa dados do Supabase 
print("Conectando ao Supabase...")
supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

# Busca em páginas de 1000 (limite do plano gratuito)
print("Baixando dados do Supabase...")
todos = []
pagina = 0
tamanho = 1000

while True:
    inicio = pagina * tamanho
    resultado = (
        supabase.table("reviews")
        .select("texto, nota, recomenda, sentimento")
        .range(inicio, inicio + tamanho - 1)
        .execute()
    )
    lote = resultado.data
    if not lote:
        break
    todos.extend(lote)
    pagina += 1
    print(f"  Página {pagina} — {len(todos)} registros baixados...")

df_raw = pd.DataFrame(todos)
print(f"\nTotal baixado: {len(df_raw)} registros")
print(df_raw.head(3))

# Limpeza de texto
print("\nAplicando limpeza de texto...")

def limpar_texto(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    texto = texto.lower()
    texto = re.sub(r"http\S+", "", texto)
    texto = re.sub(r"[^\w\sáéíóúâêîôûãõçàü]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

df_raw["texto_limpo"] = df_raw["texto"].apply(limpar_texto)

# Feature engineering com DuckDB 
print("Aplicando feature engineering com DuckDB...")
con = duckdb.connect()

# Registra o DataFrame como tabela virtual no DuckDB
con.register("reviews_raw", df_raw)

df = con.execute("""
    SELECT
        texto_limpo,
        sentimento,
        nota,
        recomenda,
        LENGTH(texto_limpo)                          AS tamanho_texto,
        ARRAY_LENGTH(STR_SPLIT(texto_limpo, ' '))    AS num_palavras,
        CASE
            WHEN nota IN (4, 5) THEN 'positivo'
            WHEN nota = 3       THEN 'neutro'
            ELSE                     'negativo'
        END AS sentimento_calculado
    FROM reviews_raw
    WHERE texto_limpo IS NOT NULL
      AND LENGTH(TRIM(texto_limpo)) > 10
      AND ARRAY_LENGTH(STR_SPLIT(texto_limpo, ' ')) >= 3
""").df()

con.close()

print(f"Registros após filtro: {len(df)}")

# Estatísticas exploratórias
print(f"\nDistribuição de sentimentos:")
print(df["sentimento"].value_counts())
print(f"\nMédia de palavras por sentimento:")
print(df.groupby("sentimento")["num_palavras"].mean().round(1))

# Salva como Parquet em data/processed/
os.makedirs("data/processed", exist_ok=True)
saida = "data/processed/reviews_processado.parquet"
df[["texto_limpo", "sentimento", "nota", "num_palavras", "tamanho_texto"]].to_parquet(
    saida, index=False
)

print(f"\nSalvo em {saida}")
print("Preprocessing concluído!")