"""
train.py
--------
Treina um classificador de sentimento (TF-IDF + Logistic Regression)
e loga tudo no MLflow. Salva o modelo em data/models/.
"""

import os
import pickle
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report
)
from sklearn.pipeline import Pipeline

# ── Parâmetros (fáceis de tunar e logar no MLflow) ────────────────────────────
PARAMS = {
    "max_features": 10000,
    "ngram_range": (1, 2),
    "max_iter": 300,
    "C": 1.0,
    "test_size": 0.2,
    "random_state": 42,
}

# ── 1. Carrega dados processados ──────────────────────────────────────────────
print("Carregando dados processados...")
df = pd.read_parquet("data/processed/reviews_processado.parquet")
df = df.dropna()

X = df["texto_limpo"]
y = df["sentimento"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=PARAMS["test_size"],
    random_state=PARAMS["random_state"],
    stratify=y
)

print(f"Treino: {len(X_train)} | Teste: {len(X_test)}")

# ── 2. Pipeline TF-IDF + Regressão Logística ─────────────────────────────────
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        max_features=PARAMS["max_features"],
        ngram_range=PARAMS["ngram_range"],
        sublinear_tf=True
    )),
    ("clf", LogisticRegression(
        max_iter=PARAMS["max_iter"],
        C=PARAMS["C"],
        class_weight="balanced"
    ))
])

# ── 3. Treina com MLflow tracking ─────────────────────────────────────────────
mlflow.set_experiment("sentimento-tiktok")

with mlflow.start_run():
    print("\nTreinando modelo...")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    f1  = f1_score(y_test, y_pred, average="weighted")

    # Loga parâmetros e métricas
    mlflow.log_params(PARAMS)
    mlflow.log_metric("accuracy", acc)
    mlflow.log_metric("f1_weighted", f1)

    # Loga o modelo
    mlflow.sklearn.log_model(pipeline, "modelo_sentimento")

    print(f"\nAcurácia : {acc:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"\n{classification_report(y_test, y_pred)}")

    run_id = mlflow.active_run().info.run_id
    print(f"\nRun ID MLflow: {run_id}")

# ── 4. Salva modelo localmente para deploy ────────────────────────────────────
os.makedirs("data/models", exist_ok=True)
with open("data/models/modelo_sentimento.pkl", "wb") as f:
    pickle.dump(pipeline, f)

print("\nModelo salvo em data/models/modelo_sentimento.pkl")
print("Treinamento concluído!")