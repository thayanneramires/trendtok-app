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
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Modelo não encontrado em {MODEL_PATH}. "
                "Execute src/train.py primeiro."
            )
        with open(MODEL_PATH, "rb") as f:
            _modelo = pickle.load(f)
    return _modelo


def prever_sentimento(textos: list[str]) -> list[dict]:
    """
    Recebe uma lista de textos e retorna lista de dicts com:
    - sentimento: 'positivo' | 'neutro' | 'negativo'
    - confianca: float (0 a 1)
    - probabilidades: dict com prob de cada classe
    - emoji: emoji correspondente ao sentimento
    """
    if not textos:
        return []

    modelo = carregar_modelo()
    classes = modelo.classes_

    probas = modelo.predict_proba(textos)
    preds  = modelo.predict(textos)

    emojis = {
        "positivo": "✅",
        "neutro":   "😐",
        "negativo": "❌"
    }

    resultados = []
    for pred, proba in zip(preds, probas):
        resultados.append({
            "sentimento":     pred,
            "confianca":      float(np.max(proba)),
            "emoji":          emojis.get(pred, "❓"),
            "probabilidades": {
                classe: float(prob)
                for classe, prob in zip(classes, proba)
            }
        })

    return resultados


def resumo_sentimentos(resultados: list[dict]) -> dict:
    """
    Recebe a lista de resultados e retorna um resumo agregado:
    - contagens por sentimento
    - percentuais
    - sentimento dominante
    - score geral (-1 a 1)
    """
    if not resultados:
        return {}

    contagem = {"positivo": 0, "neutro": 0, "negativo": 0}
    for r in resultados:
        s = r.get("sentimento", "neutro")
        contagem[s] = contagem.get(s, 0) + 1

    total = len(resultados)
    pct = {k: v / total for k, v in contagem.items()}
    score = (contagem["positivo"] - contagem["negativo"]) / total
    dominante = max(contagem, key=contagem.get)

    return {
        "total":      total,
        "contagem":   contagem,
        "percentual": pct,
        "score":      score,
        "dominante":  dominante,
    }


#  Teste rápido 
if __name__ == "__main__":
    exemplos = [
        "Produto incrível, chegou rápido e superou minhas expectativas!",
        "Péssimo, veio com defeito e o suporte não resolveu nada.",
        "O produto é ok, nada demais, faz o que promete.",
    ]

    resultados = prever_sentimento(exemplos)
    for texto, res in zip(exemplos, resultados):
        print(f"\nTexto     : {texto[:60]}")
        print(f"Sentimento: {res['emoji']} {res['sentimento']} ({res['confianca']:.0%})")

    print("\nResumo:")
    print(resumo_sentimentos(resultados))