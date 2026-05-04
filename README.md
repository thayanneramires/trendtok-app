# 📊 TrendTok — Inteligência de Hype e Sentimento

Radar de tendências com análise de sentimento de comentários do TikTok.
Identifica produtos em alta e classifica se o que falam é positivo, negativo ou neutro.

---

## 🏗️ Arquitetura

```
[API TikTok] → [Supabase] → [DuckDB] → [Feature Engineering]
                                               ↓
[DagsHub/DVC] ← [Versionamento] ← [Treinamento + MLflow]
                                               ↓
                                      [Docker Container]
                                               ↓
                                    [Render Deploy] → [Streamlit App]
```

---

## 🚀 Como rodar localmente

### 1. Clone e instale as dependências

```bash
git clone <seu-repositorio>
cd projeto-final
pip install -r requirements.txt
```

### 2. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=sua_chave_aqui
TIKTOK_API_KEY=sua_chave_tiktok
```

### 3. Configure o DVC com DagsHub

```bash
dvc remote add origin https://dagshub.com/<usuario>/<repositorio>.dvc
dvc remote modify origin --local auth basic
dvc remote modify origin --local user <usuario_dagshub>
dvc remote modify origin --local password <token_dagshub>
```

### 4. Execute o pipeline completo

```bash
# Ingere os dados e sobe no Supabase
python src/ingestion.py

# Processa os dados com DuckDB
python src/preprocessing.py

# Treina o modelo e loga no MLflow
python src/train.py

# Ou rode tudo de uma vez com DVC:
dvc repro
```

### 5. Veja os experimentos no MLflow

```bash
mlflow ui
# Acesse http://localhost:5000
```

### 6. Rode o app

```bash
streamlit run app/streamlit_app.py
```

---

## 🐳 Rodando com Docker

```bash
docker build -t tiktok-analyzer .
docker run -p 8501:8501 --env-file .env tiktok-analyzer
```

---

## 📁 Estrutura do projeto

```
projeto-final/
├── data/
│   ├── raw/                  # Dados brutos (versionados via DVC)
│   ├── processed/            # Dados processados
│   └── models/               # Modelo treinado
├── notebooks/                # EDA exploratória
├── src/
│   ├── ingestion.py          # Ingestão: HuggingFace → Supabase
│   ├── preprocessing.py      # Feature engineering com DuckDB
│   ├── train.py              # Treinamento + MLflow tracking
│   └── predict.py            # Inferência
├── app/
│   └── streamlit_app.py      # Interface do usuário
├── Dockerfile
├── requirements.txt
├── dvc.yaml                  # Pipeline DVC
└── README.md
```

---

## 🛠️ Stack

| Ferramenta | Papel |
|---|---|
| TikTok API | Fonte de dados (comentários e views) |
| Supabase | Armazenamento dos dados brutos |
| DuckDB | Queries analíticas e feature engineering |
| scikit-learn | Modelo TF-IDF + Logistic Regression |
| MLflow | Tracking de experimentos |
| DVC + DagsHub | Versionamento de dados e modelos |
| Docker | Containerização |
| Render | Deploy em produção |
| Streamlit | Interface interativa |
