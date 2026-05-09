# TrendTok — Inteligência de Hype e Sentimento

Coleta comentários de vídeos em alta no TikTok, classifica o sentimento de cada um como positivo, negativo ou neutro e exibe tudo em um painel.

---

## Por que esse projeto existe

Não existe uma forma direta de saber quais produtos estão viralizando no TikTok agora, nem se os comentários sobre eles são elogios ou reclamações. O TrendTok faz essa leitura: coleta os comentários via API, roda um modelo de classificação e mostra o resultado em um painel interativo.

O problema é de classificação de texto. Dado um comentário em português, o modelo retorna positivo, negativo ou neutro. Os dados vêm da API do TikTok via RapidAPI, com um dataset público pré-rotulado para treino inicial. A métrica de avaliação é o F1 com ponderação pelo suporte de cada classe.

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

## Decisões técnicas

O Supabase armazena os comentários brutos. Por ser um PostgreSQL gerenciado, dá para atualizar os dados de forma incremental sem reprocessar tudo do zero.

O feature engineering usa DuckDB, que roda SQL direto sobre os DataFrames sem precisar de servidor.

No treinamento, cada modelo roda dentro de um Pipeline do scikit-learn com um TF-IDF na entrada — `max_features=10000` e `ngram_range=(1, 2)` para capturar bigramas. Os dados são divididos em 80/20 com estratificação para manter a proporção das classes no treino e no teste.

Foram comparados três modelos no MLflow: Logistic Regression, Naive Bayes e SVM. Os resultados foram:

| Modelo               | Accuracy | F1 Weighted |
|----------------------|----------|-------------|
| Logistic Regression  | 0.8455   | 0.8262      |
| SVM                  | 0.8420   | 0.8230      |
| Naive Bayes          | 0.8226   | 0.8030      |

O modelo com maior F1 weighted é registrado automaticamente no MLflow Model Registry com o nome `sentimento_tiktok_model` e salvo localmente em `data/models/modelo_sentimento.pkl`.

O F1 weighted pondera o score pelo suporte de cada classe. Os dados não estavam desbalanceados a ponto de precisar de resampling, então essa métrica foi suficiente para selecionar o melhor modelo.

A aplicação roda em Docker para manter o ambiente local igual ao de produção. O Render faz rebuild a cada push na main.

---

## Como rodar localmente

Clone o repositório e instale as dependências:

```bash
git clone <seu-repositorio>
cd trendtok-app
pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz com as credenciais. O arquivo está no `.gitignore` e não será versionado:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=sua_chave_aqui
TIKTOK_API_HOST=tiktok-video-no-watermark2.p.rapidapi.com
TIKTOK_API_KEY=sua_chave_tiktok
DAGSHUB_USER=seu_usuario
DAGSHUB_REPO=trendtok-app
MLFLOW_TRACKING_URI=https://dagshub.com/<usuario>/trendtok-app.mlflow
```

Configure o DVC com o remote do DagsHub:

```bash
dvc remote add origin https://dagshub.com/<usuario>/trendtok-app.dvc
dvc remote modify origin --local auth basic
dvc remote modify origin --local user <usuario_dagshub>
dvc remote modify origin --local password <token_dagshub>
```

Para rodar o pipeline:

```bash
python src/ingestion.py
python src/preprocessing.py
python src/train.py

# ou simplesmente
dvc repro
```

Para subir o app:

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
│   └── utils.py              # Funções auxiliares e busca de dados
├── .dockerignore
├── .gitignore
├── Dockerfile
├── dvc.yaml
├── requirements.txt
└── README.md
```

---

## Deploy

`https://trendtok-app.onrender.com`