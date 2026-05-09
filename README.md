# TrendTok — Inteligência de Hype e Sentimento

Radar de tendências com análise de sentimento de comentários do TikTok. Identifica produtos em alta e classifica o que as pessoas falam como positivo, negativo ou neutro.

---

## Por que esse projeto existe

Todo mundo já viu um produto explodir no TikTok do nada. O problema é que não existe uma forma simples de acompanhar quais produtos estão viralizando agora, e muito menos saber se o que as pessoas estão comentando é elogio ou reclamação.

O TrendTok resolve exatamente isso. A gente coleta comentários de vídeos em alta via API, treina um modelo de classificação de sentimento e entrega tudo num painel interativo. O resultado é uma visão rápida de quais produtos estão em alta e se o hype é genuíno ou não.

O problema que resolvemos é de classificação: dado um comentário em português, o modelo decide se ele é positivo, negativo ou neutro. Os dados vêm da API do TikTok via RapidAPI, complementados por um dataset público pré-rotulado que usamos para dar um ponto de partida ao modelo. As métricas que guiam o projeto são F1-score macro e AUC-ROC, porque as classes não são perfeitamente balanceadas e accuracy sozinha esconderia esse problema.

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

Escolhemos o Supabase para guardar os comentários brutos porque ele entrega um PostgreSQL gerenciado sem configuração, e isso facilita atualizar os dados incrementalmente sem reprocessar tudo do zero.

Para o feature engineering usamos DuckDB, que permite escrever SQL diretamente sobre os DataFrames sem precisar subir nenhum servidor. Comparado a chains longas de pandas, o código ficou bem mais legível e o processamento mais rápido.

Treinamos três modelos e comparamos tudo no MLflow: Logistic Regression como baseline, Naive Bayes e SVM. Os resultados de validação foram os seguintes:

| Modelo               | Accuracy | F1 Weighted |
|----------------------|----------|-------------|
| Logistic Regression  | 0.8455   | 0.8262      |
| SVM                  | 0.8420   | 0.8230      |
| Naive Bayes          | 0.8226   | 0.8030      |

A Logistic Regression teve o melhor desempenho nos dois indicadores e foi o modelo registrado no Model Registry como modelo de produção.

Um detalhe importante foi o balanceamento das classes. Comentários neutros são maioria nos dados coletados, e sem tratar isso o modelo simplesmente ignoraria as classes menores. Aplicamos SMOTE só no conjunto de treino para não vazar informação para a validação.

A aplicação roda em container Docker, o que garante que o ambiente local e o de produção sejam idênticos. O Render faz rebuild automático a cada push na main, então o deploy é praticamente transparente.

---

## Como rodar localmente

Clone o repositório e instale as dependências:

```bash
git clone <seu-repositorio>
cd trendtok-app
pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz com as credenciais do projeto. O arquivo já está no `.gitignore`, então nunca será versionado:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=sua_chave_aqui
TIKTOK_API_HOST=tiktok-video-no-watermark2.p.rapidapi.com
TIKTOK_API_KEY=sua_chave_tiktok
DAGSHUB_TOKEN=seu_token_dagshub
MLFLOW_TRACKING_URI=https://dagshub.com/<usuario>/trendtok-app.mlflow
```

Configure o DVC apontando para o remote do DagsHub:

```bash
dvc remote add origin https://dagshub.com/<usuario>/trendtok-app.dvc
dvc remote modify origin --local auth basic
dvc remote modify origin --local user <usuario_dagshub>
dvc remote modify origin --local password <token_dagshub>
```

Para rodar o pipeline, você pode executar cada etapa separadamente ou usar o `dvc repro` que reconstrói tudo de uma vez de forma reprodutível — qualquer pessoa com acesso ao repositório chega nos mesmos resultados:

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
│   ├── utils.py              # Funções auxiliares e busca de dados
│   └── capa.png              # Imagem de capa
├── .dockerignore
├── .gitignore
├── Dockerfile
├── dvc.yaml
├── requirements.txt
└── README.md
```

---

## Deploy

A aplicação está disponível em `https://trendtok-app.onrender.com`