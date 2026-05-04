"""
predict.py
----------
Função de inferência reutilizável pelo Streamlit app.
Carrega o modelo treinado e retorna sentimento + probabilidades.
"""

import pickle
import numpy as np
from pathlib import Path

MODEL_PATH = Path("data/models/modelo_sentimento.pkl")

_modelo = None

def carregar_modelo():
    global _modelo
    if _modelo is None:
        with open(MODEL_PATH, "rb") as f:
            _modelo = pickle.load(f)
    return _modelo


def prever_sentimento(textos: list[str]) -> list[dict]:
    """
    Recebe uma lista de textos e retorna lista de dicts com:
    - sentimento: 'positivo' | 'neutro' | 'negativo'
    - confianca: float (0 a 1)
    - probabilidades: dict com prob de cada classe
    """
    modelo = carregar_modelo()
    classes = modelo.classes_

    probas = modelo.predict_proba(textos)
    preds  = modelo.predict(textos)

    resultados = []
    for pred, proba in zip(preds, probas):
        resultados.append({
            "sentimento":    pred,
            "confianca":     float(np.max(proba)),
            "probabilidades": {
                classe: float(prob)
                for classe, prob in zip(classes, proba)
            }
        })

    return resultados


# ── Teste rápido ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    exemplos = [
        "Produto incrível, chegou rápido e superou minhas expectativas!",
        "Péssimo, veio com defeito e o suporte não resolveu nada.",
        "O produto é ok, nada demais, faz o que promete.",
    ]

    resultados = prever_sentimento(exemplos)
    for texto, res in zip(exemplos, resultados):
        print(f"\nTexto     : {texto[:60]}...")
        print(f"Sentimento: {res['sentimento']} ({res['confianca']:.0%} confiança)")
        print(f"Probs     : { {k: f'{v:.0%}' for k, v in res['probabilidades'].items()} }")
