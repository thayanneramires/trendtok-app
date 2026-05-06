import os
import pickle
import mlflow
import mlflow.sklearn
import dagshub
import pandas as pd
from dotenv import load_dotenv

from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline

# =========================
#  Conecta com DagsHub
# =========================
load_dotenv()

dagshub.init(
    repo_name=os.getenv("DAGSHUB_REPO"),
    repo_owner=os.getenv("DAGSHUB_USER"),
    mlflow=True
)

mlflow.set_experiment("sentimento-tiktok")

# =========================
# Parâmetros
# =========================
PARAMS = {
    "max_features": 10000,
    "ngram_range": (1, 2),
    "test_size": 0.2,
    "random_state": 42,
}

# =========================
# Dados
# =========================
df = pd.read_parquet("data/processed/reviews_processado.parquet").dropna()

X = df["texto_limpo"]
y = df["sentimento"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=PARAMS["test_size"],
    random_state=PARAMS["random_state"],
    stratify=y
)

# =========================
# Modelos 
# =========================
models = {
    "logistic_regression": LogisticRegression(max_iter=300, C=1.0),
    "naive_bayes": MultinomialNB(),
    "svm": LinearSVC()
}

best_f1 = 0
best_model = None
best_name = ""

# =========================
# Treinamento
# =========================
for name, model in models.items():

    with mlflow.start_run(run_name=name):

        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                max_features=PARAMS["max_features"],
                ngram_range=PARAMS["ngram_range"]
            )),
            ("clf", model)
        ])

        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        f1  = f1_score(y_test, y_pred, average="weighted")

        # Logs
        mlflow.log_params(PARAMS)
        mlflow.log_param("model_type", name)

        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_weighted", f1)

        mlflow.set_tag("project", "trendtok")
        mlflow.set_tag("task", "sentiment-analysis")

        # Artefato (modelo)
        mlflow.sklearn.log_model(pipeline, "model")

        print(f"{name} | Acc: {acc:.4f} | F1: {f1:.4f}")

        # Guarda melhor modelo
        if f1 > best_f1:
            best_f1 = f1
            best_model = pipeline
            best_name = name

# =========================
# Registrar melhor modelo
# =========================
with mlflow.start_run(run_name="best_model"):

    mlflow.sklearn.log_model(
        best_model,
        "best_model",
        registered_model_name="sentimento_tiktok_model"
    )

print(f"\nMelhor modelo: {best_name} (F1={best_f1:.4f})")

# =========================
# Salvar local
# =========================
os.makedirs("data/models", exist_ok=True)

with open("data/models/modelo_sentimento.pkl", "wb") as f:
    pickle.dump(best_model, f)

print("Modelo salvo localmente.")