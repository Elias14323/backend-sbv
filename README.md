# Backend SBV - News Clustering & Debiasing API

Backend Python pour agrégation de news, clustering par sujets, et analyse de biais. Développé avec FastAPI, Celery, PostgreSQL (pgvector), et Mistral AI.

## 🎯 Objectifs

- Ingestion multi-sources (RSS, APIs)
- Regroupement par **sujet** (clustering sur embeddings)
- **Débiaisage** : résumé factuel + analyse des angles/biais + timeline sourcée
- API REST pour app Flutter
- Base : PostgreSQL avec pgvector
- Embeddings : Mistral AI

## 🚀 Stack Technique

- **Python 3.13**
- **FastAPI** : API HTTP + SSE
- **SQLAlchemy 2.0** (async) + asyncpg
- **Alembic** : migrations de schéma
- **Redis + Celery** : queue de jobs asynchrones
- **PostgreSQL 14** avec **pgvector** : stockage et similarité vectorielle
- **Mistral AI** : embeddings multilingues (1024 dims)
- **Trafilatura 2.0** : extraction de contenu web
- **python-simhash** : déduplication near-duplicate

## 📊 État Actuel (MVP Phase 1)

✅ **Pipeline d'ingestion RSS complet** :
- 19 articles ingérés
- 16 embeddings générés
- 3 clusters créés automatiquement
- API `/api/v1/topics` fonctionnelle

### Endpoints disponibles

```bash
# Liste des topics
GET /api/v1/topics

# Détails d'un topic (résumé, articles, scores de similarité)
GET /api/v1/topics/{id}

# Health check
GET /
```

## 🛠️ Installation & Setup

### Prérequis

- Python 3.13+
- PostgreSQL 14+ avec pgvector
- Redis
- Poetry

### Installation

```bash
# Clone le repo
git clone <repo-url>
cd "Backend sbv/backend"

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Editer .env avec vos credentials

# Run migrations
poetry run alembic upgrade head

# Start services
# Terminal 1: API
poetry run uvicorn app.main:app --reload

# Terminal 2: Celery worker
poetry run celery -A app.workers.celery_app worker --loglevel=info --concurrency=10

# Terminal 3: Trigger ingestion
poetry run python trigger_ingest.py
```

### Configuration requise (.env)

```env
DATABASE_URL=postgresql+asyncpg://user@localhost/dbname
REDIS_URL=redis://localhost:6379/0
MISTRAL_API_KEY=your_mistral_api_key
```

## 📁 Structure du Projet

```
backend/
├── alembic/              # Migrations de schéma
├── app/
│   ├── api/              # Endpoints FastAPI
│   │   ├── routes_topics.py
│   │   ├── routes_search.py
│   │   └── routes_stream.py
│   ├── core/             # Configuration & services
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── mistral.py
│   │   └── rate_limit.py
│   ├── models/           # SQLAlchemy models
│   │   ├── article.py
│   │   └── cluster.py
│   ├── services/         # Business logic
│   │   ├── ingest.py
│   │   ├── embed.py
│   │   └── clusterer.py
│   └── workers/          # Celery tasks
│       ├── celery_app.py
│       └── tasks.py
├── docker/               # Docker configs
├── pyproject.toml        # Dependencies
└── README.md
```

## 🔄 Pipeline de Traitement

```
[RSS Ingest] → [Normalize] → [Dedupe] → [Embed] → [Cluster] → [API]
```

1. **Ingestion** : Polling RSS feeds (sources configurées en DB)
2. **Normalisation** : Extraction texte (Trafilatura), canonisation URL, détection langue
3. **Déduplication** : Hash exact + simhash (Hamming distance ≤3)
4. **Embeddings** : Génération vecteurs 1024D via Mistral API
5. **Clustering** : Assignation par similarité cosine (seuil 0.75) + fenêtre 48h
6. **API** : Exposition via FastAPI

## 🐛 Problèmes Résolus

Voir [CHANGELOG.md](./CHANGELOG.md) pour la liste complète des fixes :
- Trafilatura 2.0 compatibility
- Mistral API migration
- Event loop conflicts (nest_asyncio)
- pgvector casting
- simhash uint64 overflow

## 📈 Prochaines Étapes

Voir [roadmap.md](./roadmap.md) pour le plan complet :

- [ ] Recherche hybride (Meilisearch)
- [ ] Détection d'événements & notifications
- [ ] Résumés multi-sources & analyse de biais
- [ ] Temps réel (SSE)
- [ ] Personnalisation utilisateur

## 📝 License

TBD

## 👥 Contributors

- Elias

## 🔐 Secrets & local configuration

Ne commitez jamais de fichiers contenant des secrets (par exemple `.env`, clés privées, certificats). Ce dépôt contient un fichier d'exemple `backend/.env.example` — copiez-le en `.env` localement et ne le commitez pas.

Bonnes pratiques recommandées :
- Utiliser un gestionnaire de secrets (Vault, AWS Secrets Manager, GCP Secret Manager, or similar) pour les clés en production.
- Stocker les certificats/clefs privées en dehors du dépôt (par ex. stockage chiffré ou secrets manager) et référencer leur chemin dans la configuration.
- Ajouter `.env`, `*.key`, `*.pem`, `*.crt` et `.vscode/` à `.gitignore` (déjà fait ici).

Si vous avez besoin d'aide pour configurer un secret manager ou pour créer des scripts d'initialisation, dites-le et je peux aider.
