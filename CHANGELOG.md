# Changelog - Backend SBV

## [Unreleased] - 2025-09-30

### ✅ Pipeline d'ingestion RSS complet (MVP Phase 1)

**Infrastructure mise en place :**
- PostgreSQL 14.19 local avec pgvector 0.8.1 (compilé depuis source)
- Redis localhost:6379 pour Celery message broker
- Celery workers avec 10 concurrency (prefork)
- FastAPI server sur port 8000
- Mistral AI pour embeddings (mistral-embed, 1024 dimensions)

**Base de données :**
- ✅ 3 migrations Alembic exécutées :
  - `f73907598549` : Tables sources et articles
  - `22211ae2db72` : Tables embeddings et clustering
  - `0fa290b0f956` : Vues actives pour clusters
- ✅ pgvector extension installée et fonctionnelle
- ✅ 3 sources RSS configurées (Le Monde, BBC News, TechCrunch)

**Problèmes résolus :**
1. **Trafilatura 2.0 compatibility** : Migration de `json_output=True` vers extraction en 2 étapes
   - Removed deprecated `json_output` parameter
   - Parse metadata separately with `extract_metadata()`
   
2. **Mistral API migration** : 
   - Changed from deprecated `MistralClient` to `Mistral()`
   - Fixed parameter name: `input` → `inputs` (array)
   
3. **Event loop conflicts** :
   - Added `nest_asyncio.apply()` to resolve Celery + asyncpg event loop issues
   - Fixed async/sync wrapper functions in tasks
   
4. **pgvector casting** :
   - Convert numpy arrays to string format `[x,y,z]`
   - Use `CAST(:param AS vector)` for pgvector queries
   
5. **simhash_64 overflow** :
   - Convert uint64 Simhash to signed int64 for PostgreSQL BIGINT compatibility
   
6. **Clustering logic** :
   - Allow clustering even when embedding already exists
   - Created active ClusterRun for assignment

**Résultats :**
- 📰 **19 articles** ingérés depuis Le Monde RSS
- 🧬 **16 embeddings** générés avec Mistral API
- 🎯 **3 clusters** créés automatiquement
- 🚀 **API `/api/v1/topics`** fonctionnelle

**API Endpoints testés :**
- `GET /api/v1/topics` : Liste des topics avec nombre d'articles
- `GET /api/v1/topics/{id}` : Détails du topic avec articles et scores de similarité

**Fichiers modifiés :**
- `backend/app/workers/tasks.py` : 
  - Import nest_asyncio
  - Fix Trafilatura 2.0 API
  - Fix Mistral embeddings API
  - Fix pgvector casting
  - Fix clustering logic for existing embeddings
- `backend/app/core/mistral.py` : Migration to new Mistral client
- `backend/app/core/db.py` : SSL disabled for localhost connections
- `backend/.env` : Updated Mistral API key

**Stack confirmé opérationnel :**
- [x] Python 3.13
- [x] FastAPI
- [x] SQLAlchemy 2.0 async + asyncpg
- [x] Alembic migrations
- [x] Redis + Celery
- [x] pgvector (PostgreSQL 14)
- [x] httpx + trafilatura 2.0
- [x] python-simhash
- [x] Mistral AI (embeddings)

**Prochaines étapes (roadmap.md §17) :**
- [ ] Étape 6 : Recherche hybride (Meilisearch)
- [ ] Étape 7 : Tendances, événements & notifications
- [ ] Étape 8 : Optimisation API & temps réel (SSE)
- [ ] Étape 9 : Personnalisation utilisateur
