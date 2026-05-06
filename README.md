# TrendTok — Inteligência de Hype e Sentimento

Radar de tendências com análise de sentimento de comentários do TikTok.
Identifica produtos em alta e classifica o que as pessoas falam como positivo, negativo ou neutro.

---

## Arquitetura

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

## Como rodar localmente

### 1. Clone e instale as dependências

```bash
git clone <seu-repositorio>
cd trendtok-app
pip install -r requirements.txt
```

### 2. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=sua_chave_aqui
TIKTOK_API_HOST=tiktok-video-no-watermark2.p.rapidapi.com
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

### 5. Rode o app

```bash
streamlit run app/app.py
```

---

## Rodando com Docker

```bash
docker build -t trendtok-app .
docker run -p 8501:8501 --env-file .env trendtok-app
```

Acesse em `http://localhost:8501`.

---

## Estrutura do projeto

```
trendtok-app/
├── data/
│   ├── raw/                  # Dados brutos (versionados via DVC)
│   ├── processed/            # Dados processados
│   └── models/               # Modelo treinado (.pkl)
├── src/
│   ├── ingestion.py          # Ingestão de dados → Supabase
│   ├── preprocessing.py      # Feature engineering com DuckDB
│   ├── train.py              # Treinamento + MLflow tracking
│   └── predict.py            # Inferência de sentimento
├── app/
│   ├── app.py                # Interface Streamlit
│   ├── utils.py              # Funções auxiliares e busca de dados
│   └── capa.png              # Imagem de capa
├── .dockerignore
├── .env                      # Variáveis de ambiente 
├── .gitignore
├── Dockerfile
├── dvc.yaml                  # Pipeline DVC
├── requirements.txt
└── README.md
```