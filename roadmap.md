# Backend Python (FastAPI + Celery) — Plan exécutable

> **📅 Dernière mise à jour** : 1er Octobre 2025  
> **🚀 État** : MVP Phase 1-3 complétés (Ingestion + IA + Temps réel)  
> **📊 Progression** : Étapes 0-7 + 14 terminées (voir §17)  
> **🔗 Repo GitHub** : https://github.com/Elias14323/backend-sbv

## ✅ Accomplissements récents

### Phase 1 : Pipeline de base (30/09/2025)
- ✅ Pipeline d'ingestion RSS complet opérationnel
- ✅ 19 articles ingérés, 16 embeddings, 3 clusters créés
- ✅ API `/api/v1/topics` fonctionnelle
- ✅ Fixes majeurs : Trafilatura 2.0, Mistral API, pgvector, event loops
- ✅ Repo GitHub initialisé et pushé

### Phase 2 : Résumés et Analyse IA (30/09/2025 soir)
- ✅ Table `cluster_summaries` avec versioning créée
- ✅ Service de résumé avec Mistral chat completion implémenté
- ✅ Tâche Celery `summarize_cluster` avec déclenchement automatique
- ✅ API enrichie avec résumés, bias analysis et timeline
- ✅ Test réussi : résumé de 7.4k caractères généré pour cluster de 14 articles

### Phase 3 : Détection d'événements et Streaming temps réel (1er/10/2025)
- ✅ Tables `trend_metrics` et `events` avec modèles créés
- ✅ Service trending : calcul de vélocité, accélération, nouveauté, détection d'anomalies
- ✅ Tâche Celery `calculate_trends` (analyse clusters actifs 24h)
- ✅ Tâche Celery `detect_events` (détection de pics, sévérités low/medium/high/critical)
- ✅ Endpoint SSE `/api/v1/stream/events` avec Redis Pub/Sub
- ✅ Test end-to-end : client SSE reçoit événements en temps réel via Redis
- ✅ Backend véritablement **vivant** : peut pousser breaking news instantanément

---

## 0) Objectifs

- [ ] Ingestion multi-sources (RSS, APIs sociales, scraping si autorisé)
- [ ] Regroupement par **sujet** (clustering sur embeddings)
- [ ] **Débiaisage**: résumé factuel + analyse des angles/biais + timeline sourcée
- [ ] API pour Flutter (+ temps réel)
- [ ] Base: **Supabase Postgres** (pgvector) — pas de Supabase Functions
- [ ] **Mistral** pour embeddings + génération

## 0bis) Fonctionnalités nécessaires (détaillées)

**Ingestion (pragmatique)**

- [ ] **MVP** : **RSS/Atom + APIs officielles** uniquement (pas de crawler autonome).
- [ ] **Phase 2** : + **sitemaps** et **scrapers ciblés** (quelques sources prioritaires sans bon flux).
- [ ] **Phase 3** : crawler complet (frontier, découverte de liens) si ROI avéré.

**Normalisation & qualité**

- [ ] Canonisation d’URL, extraction de texte, détection de langue, timezone, auteur/source, estimation de qualité (bruit, longueur utile, duplication).
- [ ] Déduplication (hash exact + simhash) et marquage.

**Vectorisation & recherche**

- [ ] Embeddings multilingues, stockage vecteur, recherche sémantique (kNN), plein‑texte tolérant aux fautes.

**Clustering par sujet**

- [ ] Attribution en flux (seuil de similarité + fenêtre glissante), fusion/scission périodiques, étiquetage automatique.

**Résumé & “bias breakdown”**

- [ ] Résumé factuel multi‑sources, angles/biais, accords/désaccords, timeline datée, lacunes, références.

**Détection d’évènements & notifications**

- [ ] Volume/vélocité/accélération/novelty/locality + corroboration multi‑sources.
- [ ] Règles d’alerte (entités, mots‑clés, zones, sévérité, quiet hours), push FCM, déduplication.

**Personnalisation & UX**

- [ ] Abonnements (entité/sujet/mot‑clé/lieu), favoris, feedback, préférences de langue.

**Administration & observabilité**

- [ ] Dashboards sources/queues, coûts LLM, métriques SLO, traces/logs, reprocessing.

**Sécurité & conformité**

- [ ] Auth, RBAC, RGPD (export/suppression), chiffrement, gestion secrets.

---

## 1) Stack de référence (Python-first)

- [x] **Python** 3.13 ✅
- [x] **FastAPI** (API HTTP + SSE/WebSocket) ✅ 30/09/2025
- [x] **SQLAlchemy 2.0** (async) + **asyncpg** (PostgreSQL 14 local) + **Alembic** (migrations) ✅ 30/09/2025
- [x] **Redis** (broker/queue) + **Celery** (workers + retries + DLQ) ✅ 30/09/2025
- [ ] **Meilisearch** (recherche tolérante aux fautes)
- [x] **pgvector** (similarité via cosine dans Postgres) ✅ 30/09/2025
- [x] **httpx** (async HTTP), **trafilatura 2.0** (extraction), **Playwright** (pages JS) ✅ 30/09/2025
- [x] **langdetect** ou **fasttext-langdetect** (langue), **tldextract** (canonisation), **python-simhash** (near-duplicates) ✅ 30/09/2025
- [ ] **prometheus-fastapi-instrumentator** (métriques), **structlog** (logs), **OpenTelemetry** (optionnel)

> Alternative queue: **Dramatiq** (Redis/Rabbit). Si vous voulez plus simple que Celery, Dramatiq est excellent.

---

## 2) Architecture & flux

```
[ingest] -> [normalize] -> [dedupe] -> [embed] -> [cluster] -> [summarize]
                              |              |               |
                            DB write       DB write        DB write
```

- [ ] Chaque étape = **job Celery** idempotent (clé: URL canonique).
- [ ] **Rate limiting** par domaine, **backoff** exponentiel, **DLQ** sur échecs.
- [ ] **Fenêtre glissante** 24–72h pour le clustering.

## 2bis) Structure de fonctionnement du backend (modules & responsabilités)

- [ ] **API Gateway (FastAPI)** : endpoints publics (topics, recherche, sources, abonnements), SSE/WebSocket pour temps réel, auth.
- [ ] **Orchestrateur de jobs (Celery/Redis)** : planification, priorités, retries, DLQ, idempotence.
- [ ] **Service Ingestion** : lecture RSS/APIs, découverte via sitemaps/liens, alimentation de la frontier.
- [ ] **Service Fetch/Extract** : téléchargement (politeness), extraction texte/métadonnées, normalisation.
- [ ] **Service Dédoublonnage** : hash exact, simhash, marquage et routage vers indexation si unique.
- [ ] **Service Embeddings** : appels LLM d’embedding, stockage pgvector, index kNN.
- [ ] **Service Clustering** : assignation en flux, fusion/scission périodiques, étiquetage.
- [ ] **Service Résumé/Biais** : agrégation multi‑sources, génération contrôlée, stockage markdown.
- [ ] **Service Recherche** : indexation Meilisearch, synonymes/stop‑words, filtres.
- [ ] **Service Tendance/Évènements** : calcul métriques, bursts, corroboration.
- [ ] **Service Notifications** : appariement règles, construction payload, envoi FCM/e‑mail, journalisation.
- [ ] **Admin/Observabilité** : métriques, logs, traces, dashboards, outils de reprocessing.

---

## 2ter) Stratégie d’ingestion par phases (pragmatique)

- [ ] **Phase 1 (MVP)** : **RSS/Atom + APIs** — focus sur clustering, résumés/biais, temps réel, recherche, notifs.
- [ ] **Phase 2** : **Sitemaps + scrapers ciblés** — combler les sources prioritaires sans flux.
- [ ] **Phase 3** : **Crawler autonome** — seulement si ROI/ressources, pour exhaustivité.

---

## 3) Schéma Postgres (Supabase) — **unifié v1**

> Objectif : cohérence, versionnement natif, A/B facile, extensible vers IA locale, **sans casser l’API**.

### 3.1 Sources & santé

**✅ Créée (migration f73907598549)**

````sql
create table sources (
  id bigserial primary key,
  name text not null,
  url text not null unique,
  kind text check (kind in ('rss','site','social','api')) not null,
  country_code text,              -- ISO 3166-1 alpha-2 (pays d'immatriculation)
  lang_default text,              -- langue principale du média
  trust_tier text check (trust_tier in ('A','B','C')) default 'B',
  political_axis jsonb,           -- {"left_right": -1..+1, "auth_lib": -1..+1}
  scope text check (scope in ('local','regional','national','international')) default 'national',
  home_area_id bigint,            -- FK logique vers geo_areas (défini en §3.13)
  last_fetch_at timestamptz,
  error_rate real default 0,
  created_at timestamptz default now()
);
```sql
create table sources (
  id bigserial primary key,
  name text not null,
  url text not null unique,
  kind text check (kind in ('rss','site','social','api')) not null,
  country_code text,              -- ISO 3166-1 alpha-2
  lang_default text,              -- langue principale du média
  trust_tier text check (trust_tier in ('A','B','C')) default 'B',
  political_axis jsonb,           -- ex: {"left_right": -0.3, "auth_lib": 0.1}
  topics jsonb,                   -- thématiques principales déclarées
  last_fetch_at timestamptz,
  error_rate real default 0,
  created_at timestamptz default now()
);
````

### 3.2 Articles & duplication

**✅ Créée (migration f73907598549)**

```sql
create table articles (
  id bigserial primary key,
  source_id bigint references sources(id) on delete cascade,
  url text unique,
  url_canonical text,
  title text,
  author text,
  lang text,
  published_at timestamptz,
  raw_html text,
  text_content text,
  hash_64 bytea,
  simhash_64 bigint,
  quality_score real,
  created_at timestamptz default now()
);

-- Liens de duplication
create table article_duplicates (
  article_id bigint references articles(id) on delete cascade,
  duplicate_of_id bigint references articles(id) on delete cascade,
  kind text check (kind in ('exact','near')) not null,
  distance int,                    -- hamming pour near dup
  primary key (article_id)
);
create index on articles (published_at desc);
create index on articles (url_canonical);
```

### 3.3 Embeddings **multi-espaces** (A/B prêt)

**✅ Créée (migration 22211ae2db72)** — _Note: table nommée `article_embeddings` au lieu de `article_embeddings_multi`_

```sql
create table embedding_spaces (
  id bigserial primary key,
  name text not null,
  provider text not null,    -- 'mistral','oss-local',...
  dims int not null,
  version text,
  notes text,
  created_at timestamptz default now(),
  unique(name, version)
);

create table article_embeddings_multi (
  space_id bigint references embedding_spaces(id),
  article_id bigint references articles(id) on delete cascade,
  embedding vector(1024),
  primary key (space_id, article_id)
);
create index article_embeddings_multi_vec on article_embeddings_multi using ivfflat (embedding vector_cosine_ops);
```

### 3.4 Clustering **versionné uniquement** + vues actives

**✅ Créée (migration 22211ae2db72)** — _Note: tables nommées `clusters`/`article_clusters` au lieu de `clusters_v`/`article_cluster_v`, vues pas encore créées_

```sql
create table cluster_runs (
  id bigserial primary key,
  space_id bigint references embedding_spaces(id),
  algo text not null,                 -- 'threshold+communities','hdbscan', ...
  params jsonb not null,
  started_at timestamptz default now(),
  finished_at timestamptz,
  status text check (status in ('running','complete','failed')),
  is_active boolean default false,
  notes text
);

create table clusters_v (
  id bigserial primary key,
  run_id bigint references cluster_runs(id) on delete cascade,
  label text,
  window_start timestamptz,
  window_end timestamptz,
  created_at timestamptz default now()
);

create table article_cluster_v (
  run_id bigint references cluster_runs(id) on delete cascade,
  cluster_id bigint references clusters_v(id) on delete cascade,
  article_id bigint references articles(id) on delete cascade,
  similarity real,
  primary key (run_id, cluster_id, article_id)
);

create view v_clusters_active as
  select c.* from clusters_v c join cluster_runs r on r.id=c.run_id where r.is_active;
create view v_article_cluster_active as
  select ac.* from article_cluster_v ac join cluster_runs r on r.id=ac.run_id where r.is_active;
```

### 3.5 Résumés & biais **versionnés** + langue

**❌ Pas encore créée**

```sql
create table cluster_summaries_v (
  run_id bigint references cluster_runs(id) on delete cascade,
  cluster_id bigint references clusters_v(id) on delete cascade,
  engine text not null,            -- 'mistral','local-llm'
  engine_version text,
  lang text not null default 'en', -- langue du rendu
  summary_md text,
  bias_md text,
  timeline_md text,
  sources jsonb,
  created_at timestamptz default now(),
  primary key (run_id, cluster_id, engine, engine_version, lang)
);
```

### 3.6 Entités & géo (KG light)

```sql
create table entities (
  id bigserial primary key,
  kind text check (kind in ('person','org','place','event','other')),
  name text not null,
  aliases text[],
  external_ids jsonb,
  created_at timestamptz default now()
);

create table geo_areas (
  id bigserial primary key,
  kind text check (kind in ('country','admin1','admin2','city','custom_bbox')) not null,
  code text,                      -- ex: FR, FR-75, code INSEE, etc.
  name text not null,
  parent_id bigint references geo_areas(id),
  centroid geometry,              -- optionnel: PostGIS
  bbox geometry,                  -- optionnel: PostGIS
  population int
);

create table source_geo_coverage (
  source_id bigint references sources(id) on delete cascade,
  area_id bigint references geo_areas(id) on delete cascade,
  level text check (level in ('primary','secondary')) default 'primary',
  weight real default 1.0,
  primary key (source_id, area_id)
);

create table places (
  id bigserial primary key,
  toponym text,
  geonames_id bigint,
  osm_id text,
  centroid geometry,
  country_code text
);

create table article_entities (
  article_id bigint references articles(id) on delete cascade,
  entity_id bigint references entities(id) on delete cascade,
  salience real,
  spans jsonb,
  primary key (article_id, entity_id)
);

create table article_geo (
  article_id bigint primary key references articles(id) on delete cascade,
  area_id bigint references geo_areas(id),
  method text,                    -- 'ner','schema_org','source_default','url_path','tld'
  confidence real
);
```

**Remarques** : `sources.home_area_id` peut pointer vers un `geo_areas` (ville/région/pays) pour la racine géo du média.sql
create table entities (
id bigserial primary key,
kind text check (kind in ('person','org','place','event','other')),
name text not null,
aliases text[],
external_ids jsonb,             -- wikidata, isni, etc.
created_at timestamptz default now()
);

create table article_entities (
article_id bigint references articles(id) on delete cascade,
entity_id bigint references entities(id) on delete cascade,
salience real,
spans jsonb,                    -- offsets par langue
primary key (article_id, entity_id)
);

create table places (
id bigserial primary key,
toponym text,
geonames_id bigint,
osm_id text,
centroid geometry,              -- optionnel: PostGIS si activé
country_code text
);

````

### 3.7 Évènements & tendances

**✅ Créées (migration 9897e6a21d7f)** — 1er Octobre 2025

```sql
create table trend_metrics (
  ts timestamptz not null,
  cluster_id bigint references clusters_v(id) on delete cascade,
  run_id bigint references cluster_runs(id) on delete cascade,
  doc_count int,
  unique_sources int,
  velocity real,
  acceleration real,
  novelty real,
  locality real,                  -- 0..1 (proportion d'articles fortement localisés)
  primary key (ts, cluster_id, run_id)
);

create table cluster_locations (
  run_id bigint references cluster_runs(id) on delete cascade,
  cluster_id bigint references clusters_v(id) on delete cascade,
  area_id bigint references geo_areas(id) on delete cascade,
  weight real,                    -- importance dans le cluster
  primary key (run_id, cluster_id, area_id)
);

create table events (
  id bigserial primary key,
  run_id bigint references cluster_runs(id) on delete cascade,
  cluster_id bigint references clusters_v(id) on delete cascade,
  detected_at timestamptz not null default now(),
  score real not null,
  severity text check (severity in ('low','medium','high','critical')),
  label text,
  window_start timestamptz,
  window_end timestamptz
);
````

### 3.8 Notifications & préférences utilisateur

```sql
-- Supabase Auth gère les utilisateurs; profil local complémentaire
create table user_profiles (
  user_id uuid primary key,             -- = auth.uid
  preferred_lang text default 'en',
  created_at timestamptz default now()
);

create table user_devices (
  id bigserial primary key,
  user_id uuid not null,
  fcm_token text not null,
  platform text check (platform in ('ios','android','web')) not null,
  created_at timestamptz default now()
);

create table subscriptions (
  id bigserial primary key,
  user_id uuid not null,
  kind text check (kind in ('entity','topic','keyword','location')) not null,
  value text not null,
  lang text,
  min_severity text default 'medium',
  quiet_hours int4range,
  created_at timestamptz default now()
);

create table notifications (
  id bigserial primary key,
  user_id uuid not null,
  event_id bigint references events(id) on delete cascade,
  title text,
  body text,
  sent_at timestamptz,
  dedupe_key text,
  channel text check (channel in ('push')) not null default 'push',
  status text check (status in ('scheduled','sent','failed')) not null default 'scheduled'
);
create unique index on notifications (user_id, dedupe_key);
```

### 3.9 Sélection des sources par l’utilisateur & **bundles politiques/thématiques**

````sql
create table source_profiles (
  source_id bigint primary key references sources(id) on delete cascade,
  political_axis jsonb,           -- {left_right: -1..+1, auth_lib: -1..+1}
  tags text[]                     -- ex: ['investigation','opinion','public-broadcaster']
);

create table categories (
  id bigserial primary key,
  slug text unique not null,      -- ex: 'general','politics','sports','motorsports','tech','business','culture','science','health','local'
  name text not null,
  parent_id bigint references categories(id),
  description text
);

create table source_categories (
  source_id bigint references sources(id) on delete cascade,
  category_id bigint references categories(id) on delete cascade,
  primary key (source_id, category_id)
);

create table bundles (
  id bigserial primary key,
  name text not null,             -- ex: 'Gauche FR', 'Centre US', 'Conservateur UK', 'Sports FR'
  description text,
  axis_filter jsonb,              -- plage sur axes politique (optionnel)
  category_filter bigint,         -- FK vers categories (optionnel)
  area_filter bigint              -- FK vers geo_areas (optionnel)
);

create table bundle_sources (
  bundle_id bigint references bundles(id) on delete cascade,
  source_id bigint references sources(id) on delete cascade,
  primary key (bundle_id, source_id)
);

create table user_sources (
  user_id uuid not null,
  source_id bigint not null references sources(id) on delete cascade,
  primary key (user_id, source_id)
);

create table user_bundles (
  user_id uuid not null,
  bundle_id bigint not null references bundles(id) on delete cascade,
  primary key (user_id, bundle_id)
);
```sql
create table source_profiles (
  source_id bigint primary key references sources(id) on delete cascade,
  political_axis jsonb,           -- {left_right: -1..+1, auth_lib: -1..+1}
  tags text[]                     -- ex: ['investigation','opinion','public-broadcaster']
);

create table bundles (
  id bigserial primary key,
  name text not null,             -- ex: 'Gauche FR', 'Centre US', 'Conservateur UK'
  description text,
  axis_filter jsonb               -- plage sur axes politique
);

create table bundle_sources (
  bundle_id bigint references bundles(id) on delete cascade,
  source_id bigint references sources(id) on delete cascade,
  primary key (bundle_id, source_id)
);

create table user_sources (
  user_id uuid not null,
  source_id bigint not null references sources(id) on delete cascade,
  primary key (user_id, source_id)
);

create table user_bundles (
  user_id uuid not null,
  bundle_id bigint not null references bundles(id) on delete cascade,
  primary key (user_id, bundle_id)
);
````

### 3.10 Biais au **niveau article** (score & justification)

```sql
create table article_bias_labels (
  article_id bigint primary key references articles(id) on delete cascade,
  left_right real,                 -- -1 (gauche) ... +1 (droite)
  auth_lib real,                   -- -1 (libertaire) ... +1 (autoritaire)
  confidence real,                 -- 0..1
  cues jsonb,                      -- indices détectés (lexique, cadrage, sources citées)
  model text,                      -- moteur/heuristiques
  created_at timestamptz default now()
);
```

### 3.11 A/B tests & feature flags

```sql
create table feature_flags (
  key text primary key,
  value jsonb,
  description text
);

create table ab_tests (
  id bigserial primary key,
  name text,
  run_id bigint references cluster_runs(id),
  created_at timestamptz default now()
);

create table ab_buckets (
  test_id bigint references ab_tests(id) on delete cascade,
  user_id uuid,
  bucket text check (bucket in ('control','variant')),
  primary key (test_id, user_id)
);
```

### 3.12 Partitionnement & rétention (métadonnées)

```sql
create table retention_policies (
  table_name text primary key,
  keep_days int not null,
  notes text
);
```

---

## 4) Dossiers (monorepo simple)

```
backend/
  app/
    api/
      __init__.py
      deps.py
      routes_topics.py
      routes_search.py
      routes_stream.py
    core/
      config.py
      logging.py
      db.py
      meili.py
      mistral.py
      rate_limit.py
    models/
      base.py
      article.py
      cluster.py
    services/
      ingest.py
      normalize.py
      dedupe.py
      embed.py
      clusterer.py
      summarize.py
    workers/
      celery_app.py
      tasks.py
  alembic/
  pyproject.toml
  docker/
    Dockerfile.api
    Dockerfile.worker
    docker-compose.yml
```

---

## 5) Dépendances (liste, sans code)

- [ ] **Runtime** : Python ≥ 3.13
- [ ] **API** : FastAPI, Uvicorn
- [ ] **DB/ORM** : SQLAlchemy 2.x (async), asyncpg, Alembic (migrations)
- [ ] **Queue** : Redis, Celery (ou Dramatiq en alternative)
- [ ] **HTTP & parsing** : httpx, trafilatura/readability‑lxml, Playwright (pages dynamiques)
- [ ] **Langue & dédoublonnage** : détecteur de langue (langdetect/fastText), tldextract, simhash
- [ ] **Vecteurs & recherche** : pgvector (Postgres), Meilisearch
- [ ] **Observabilité** : structlog, Prometheus instrumentator, OpenTelemetry (optionnel)
- [ ] **Sécurité** : libs JWT/OAuth2, gestion secrets (Vault/SM) côté infra

---

## 6) Configuration & secrets (principaux paramètres)

- [ ] **DATABASE_URL / SYNC_DATABASE_URL** : connexions Postgres (async/sync) vers Supabase.
- [ ] **REDIS_URL** : broker/stockage états de jobs.
- [ ] **MEILI_HOST / MEILI_KEY** : accès Meilisearch.
- [ ] **MISTRAL_API_KEY** : clé API pour embeddings & génération.
- [ ] **CLUSTER_COSINE_THRESHOLD** : seuil de similarité (ex. 0,75–0,82 selon tuning).
- [ ] **CLUSTER_WINDOW_HOURS** : fenêtre temporelle (ex. 24–72h) pour l’assignation.
- [ ] **CRAWL_BUDGETS** : quotas par domaine (req/min, connexions, plages).
- [ ] **ALERT_DEFAULTS** : seuils par défaut pour la détection d’évènements/règles.
- [ ] **TZ_DEFAULT** : Europe/Paris.

---

## 7) API — spécification (sans code)

**Endpoints principaux**

- [ ] `GET /topics` : liste paginée des sujets de la **run active**; filtres: `category`, `area_id`, `country_code`, `scope`, `lang`, `bundle`, `since`.
- [x] `GET /topics/{id}` : résumé(s), biais, timeline, **cluster_locations**, sources, articles représentatifs. **✅ Implémenté (30/09)**
- [ ] `GET /events` : évènements triés par sévérité/date; filtres: `area_id`, `near=lat,lng&radius`, `country_code`, `category`, `lang`.
- [ ] `GET /search` : recherche mixte avec filtres (langue, source, période, **category**, **area_id**, bundle).
- [ ] `GET /sources` : catalogue + métriques + **catégories** + **couverture géo**.
- [ ] `GET /bundles` : listes politiques/thématiques et/ou géographiques (ex. *Île‑de‑France Local*).
- [ ] `POST /user/sources` / `DELETE /user/sources/{id}` : sélection/désélection de sources.
- [ ] `POST /user/bundles` / `DELETE /user/bundles/{id}` : abonnement bundles.
- [ ] `POST /subscriptions` : `kind` in (`entity`,`topic`,`keyword`,`location`), payload peut référencer `area_id` ou `near`.
- [x] `GET /stream/events` : SSE pour nouveaux événements. **✅ Implémenté (1er/10)**
- [ ] `GET /stream/topics` : SSE pour nouveaux sujets.
- [ ] `GET /health` / `GET /metrics`.

**Contrats** : toujours renvoyer `run_id`, `space_id`, et si applicable une **liste d’aires géo** avec `weight`.

---

## 8) Orchestration des jobs — pseudo‑code

**MVP path (Phase 1)**

- [ ] **ingest(source)** → lire **RSS/APIs** → nouvelles URLs → **extract**
- [ ] **extract(page)** → texte + métadonnées + entities/places → **dedupe**
- [ ] **dedupe(article)** → skip si doublon ; sinon **embed**
- [ ] **embed(article)** → vecteur (espace actif) → **cluster_assign**
- [ ] **cluster_assign(article)** → lier cluster (run active) + mettre à jour `cluster_locations`
- [ ] **cluster_maintain()** (périodique) → fusion/scission + labels
- [ ] **summarize(cluster)** → dossier EN + locales à la demande
- [ ] **trend_tick()** → `trend_metrics` → **event_detect()** (global/local)
- [ ] **notify(event)** → règles d’abonnements → push FCM

**Phase 2+ (optionnel)**

- [ ] Ajouter **sitemaps** dans `ingest` et **scrapers ciblés** dans `extract`.
- [ ] Phase 3 : introduire **frontier** et tâches `crawl_fetch` dédiées.

---

## 9) Normalisation & dédoublonnage — pseudo‑code

**canonical_url(url)** : retirer UTM, trier query, normaliser schéma/host/trailing slash, suivre `<link rel=canonical>`.
**extract_text(html)** : boilerplate removal, titre/sous‑titre, corps, auteurs, date, langue.
**quality_gate(text)** : longueur utile minimale, ratio bruit/texte, encodage OK.
**exact_duplicate?** : `hash_64` égal → marquer `duplicate_of`.
**near_duplicate?** : `simhash` distance de Hamming ≤ 3 dans fenêtre 72h → marquer `near_duplicate_of`.
**route** : si unique → continuer pipeline ; sinon, uniquement comptage/statistiques.

---

## 10) Embeddings & stockage — pseudo‑code

- [ ] **Choix figé** : **multi‑espaces** (table `article_embeddings_multi` + `embedding_spaces`) pour A/B facile, migrations et coexistence IA locale/cloud.
- [ ] **Politique** : un **espace canonique actif** pour la production; backfill d’un nouvel espace en **shadow** avant bascule.
- [ ] **Index** : ivfflat (cosine) avec paramétrage probes adapté au volume; compression si nécessaire.

---

## 11) Clustering en flux — pseudo‑code (versionné uniquement)

1. Sur nouveau document → voisins kNN dans l’**espace actif** et la **fenêtre**.
2. Si `max_cosine ≥ τ` et voisins partagent un cluster dominant (dans **run active**) → **assigner**.
3. Sinon → **créer** cluster dans `clusters_v` (lié à la **run active**).
4. **Job périodique** (par run) : graphe (cosine ≥ τ) → communautés (Louvain/Leiden) → fusion/scission, mise à jour labels.
5. Changement d’algo/params → **nouvelle run** (shadow), puis bascule en `is_active=true`.

---

## 12) Résumé “bias breakdown” — logique, langues & **localité**

- [ ] **Canonical EN** stocké, **locales à la demande** (cache court) pour l’UX.
- [ ] **Localité** : si `cluster_locations` fortement concentré dans un `geo_area`, inclure un **chapeau** (ex.: *Évènement principalement localisé à Marseille, FR-13*).
- [ ] **Transparence** : URLs, séparation FAITS/ALLÉGATIONS, mention du **périmètre géo** si pertinent.
- [ ] **Coût** : gating par taille/score/locality.

---

## 13) Recherche — Meilisearch

- [ ] Index `articles_search` avec `{ id, title, text_excerpt, lang, source, published_at }`
- [ ] Attributs filtrables: `lang`, `source`
- [ ] Synonymes et stop-words FR/EN
- [ ] Backfill à l’ingestion + mises à jour

---

## 14) Temps réel (Flutter)

- [x] **SSE** `/stream/events` pour événements breaking news. **✅ Implémenté (1er/10)** avec Redis Pub/Sub
- [ ] **SSE** `/stream/topics` pour nouveaux clusters (léger, compatible mobile)
- [ ] Option **WebSocket** pour commentaires/feedback utilisateur
- [ ] **Cache Redis** pour `/topics` et `/topics/{id}`

---

## 15) Topologie des services (dev/prod) — sans code

- [ ] **api** : FastAPI + endpoints + SSE ; dépend de Postgres, Redis, Meilisearch ; s’appuie sur `v_*_active`.
- [ ] **worker** : exécute les jobs Celery (ingest/normalize/embed/cluster/summarize/notify/trends).
- [ ] **beat/scheduler** : planifie tâches périodiques (frontier, tendances, reclustering, compaction index, purge rétention).
- [ ] **redis** : broker & backend de tâches.
- [ ] **meilisearch** : moteur plein‑texte (voir spéc §18bis).
- [ ] **postgres (Supabase managé)** : base principale avec pgvector et vues actives.

---

## 16) Observabilité & robustesse

- [ ] **Logs** JSON (structlog), **corrélation** par `article_id`/`cluster_id`
- [ ] **Métriques**: taux d’échec par étape, latence extraction/LLM, nombre de clusters actifs, coût LLM estimé
- [ ] **Rate limiting** par domaine (ingestion), **robots.txt** & ToS respectés
- [ ] **RGPD**: effacement des données utilisateur (si comptes), journal d’accès, minimisation

---

## 17) Plan par étapes (MVP → Full Feature)

> Organisation concrète, **sans code**, avec livrables et critères de sortie.

### Étape 0 — Cadre & environnements

- [ ] **Objectifs** : bases propres, secrets, observabilité, politiques de rétention (365j).
- [ ] **Livrables** : variables de config documentées, métriques/healthchecks, migrations initiales (tables cœur), jeu de sources seed.
- [ ] **Critères de sortie** : métriques exposées; DB accessible; quotas LLM désactivés par défaut (feature flag).

### Étape 1 — Ingestion Phase 1 (RSS/Atom + APIs)

- [ ] **Objectifs** : polling 50–200 sources FR/EN, idempotence, qualité de flux.
- [ ] **Livrables** : sources remplies (catégories, scope, geo coverage), planification polling, file d’URLs.
- [ ] **Critères** : ≥50 sources actives; P95 « flux→article » ≤ 2 min; taux d’erreur < 2%.

### Étape 2 — Normalisation & dédoublonnage

- [ ] **Objectifs** : extraction texte fiable, canonisation URL, langue, hash + simhash.
- [ ] **Livrables** : règles qualité (longueur utile, bruit), marquage `article_duplicates`.
- [ ] **Critères** : >95% d’articles valides; near‑dup détectés (hamming ≤3) sur reprises d’agences.

### Étape 3 — Embeddings & similarité (espace actif)

- [ ] **Objectifs** : embeddings multilingues, stockage vecteur multi‑espaces, kNN.
- [ ] **Livrables** : `embedding_spaces` (espace canonique), index vectoriel opérationnel.
- [ ] **Critères** : requêtes kNN < 200 ms p95 sur fenêtre 48–72h.

### Étape 4 — Clustering versionné (run active)

- [ ] **Objectifs** : assignation en flux, fusion/scission périodiques, labels courts.
- [ ] **Livrables** : `cluster_runs` active, `clusters_v`, `article_cluster_v`, vues `v_*_active`.
- [ ] **Critères** : cohérence thématique (échantillon manuel), taille médiane de cluster raisonnable.

### Étape 5 — Résumé & “bias breakdown”

- [ ] **Objectifs** : dossier **canonical EN** (facts vs claims, angles/biais, timeline, sources).
- [ ] **Livrables** : `cluster_summaries_v` (EN), cache pour variantes locales à la demande.
- [ ] **Critères** : 90% des clusters « matures » avec résumé sous 2 min.

### Étape 6 — Recherche hybride

- [ ] **Objectifs** : plein‑texte (Meili) + filtres (langue, source, période, catégorie, zone, bundle).
- [ ] **Livrables** : index minimal aligné schéma; stratégie synonyms/stop‑words FR/EN.
- [ ] **Critères** : latence recherche < 300 ms p95; tolérance fautes fonctionnelle.

### Étape 7 — Tendances, évènements & notifications (push)

- [ ] **Objectifs** : scores volume/velocity/acceleration/novelty/locality; détection global/local; FCM.
- [ ] **Livrables** : `trend_metrics`, `events`, règles minimas; canal `/stream/events`.
- [ ] **Critères** : alerte envoyée pour un évènement test en < 60 s post‑détection; dédup OK.

### Étape 8 — API & temps réel (SSE)

- [x] **Objectifs** : endpoints `topics`, `topics/{id}`, `events`, `search`, `sources`, `bundles`; flux SSE. **✅ Partiellement (1er/10)**
- [x] **Livrables** : contrats JSON stables (incl. `run_id`, `space_id`). **✅ `/api/v1/topics/{id}` et `/stream/events` opérationnels**
- [ ] **Critères** : Flutter affiche liste sujets, fiche sujet (résumé/biais/timeline/sources), recherche et flux live.

### Étape 9 — Personnalisation (sources, bundles, abonnements)

- [ ] **Objectifs** : sélection fine et par **bord politique/thématique/géo**; subscriptions par entité/sujet/mot‑clé/zone.
- [ ] **Livrables** : `user_sources`, `user_bundles`, `subscriptions` opérationnels.
- [ ] **Critères** : filtres/bundles pilotent effectivement l’ingestion et les notifs.

### Étape 10 — Observabilité & SLOs

- [ ] **Objectifs** : tableaux de bord pipeline/coûts, alertes techniques, backpressure.
- [ ] **Livrables** : métriques clés, budgets LLM, rapports rétention.
- [ ] **Critères** : SLOs atteints (voir §29), runbook incident de base.

**MVP = Étapes 0 → 8 (min) ; 0 → 10 (reco).**

---

## 18) Tests & qualité

- [ ] **Fixtures** HTML pour extraction; tests dorés (golden) de normalisation.
- [ ] Tests unitaires: dédoublonnage (hash/simhash), kNN pgvector, agrégation entités, labellisation biais.
- [ ] Tests E2E: pipeline complet, idempotence, bascule de run (shadow → active) sans downtime.
- [ ] Tests performance: quotas crawl, latence assignation cluster, coût/rate des LLM (si activés).

---

## 19) Notes déploiement

- [ ] Docker images séparées (API vs Worker)
- [ ] Variables d’env prod (Supabase, Mistral) via secret manager
- [ ] Auto-migrations Alembic au boot (avec prudence)
- [ ] Stratégie de **backfill** initial (batch embeddings + throttling)

---

## 20) Crawl autonome (discovery + frontier)

- [ ] **Seeds**: RSS/sitemaps officiels, pages "dernières actus", listes curées.
- [ ] **Découverte**: parsing **sitemaps**, liens internes (nofollow respecté), `<link rel=canonical>`, JSON‑LD (`extruct`) pour métadonnées.
- [ ] **Politeness**: respect **robots.txt** (cache local), `crawl-delay`, user‑agent dédié, **budget par domaine** (req/min, connexions), fenêtres horaires.
- [ ] **Frontier** (priorité): fraîcheur source, autorité, vitesse de publication passée, nouveauté d'URL, pénalité d'erreurs.
- [ ] **Fetch**: `HEAD` pour filtrer (type/taille), `GET` avec timeouts, détection paywall légère, fallback Playwright.
- [ ] **Idempotence**: URL canonique + hash contenu.
- [ ] **Internationalisation**: préférer langue FR/EN mais conserver autres langues si très corrélé au cluster.
- [ ] **Erreurs**: backoff exponentiel, **DLQ** par type (DNS, 403, 5xx…)

**Tables (extrait)**

```sql
create table crawl_frontier (
  id bigserial primary key,
  url text unique,
  source_id bigint references sources(id),
  priority real default 0,
  last_fetch_at timestamptz,
  fail_count int default 0,
  status text check (status in ('new','enqueued','fetched','blocked','error')) default 'new'
);

create table robots_cache (
  host text primary key,
  fetched_at timestamptz,
  policy text
);
```

**Workers dédiés** : `crawl_discover`, `crawl_fetch`, `extract_links`, puis `normalize`.

**Beat (planification)**

- [ ] t+60s: batch `crawl_frontier` → `crawl_fetch` (quota par domaine)
- [ ] t+15m: refresh sitemaps & sources
- [ ] t+15m: reclustering communautaire
- [ ] t+5m: calcul métriques de tendance (cf. §21)

---

## 21) Détection d’évènements majeurs (bursts & corroboration)

**Objectif** : repérer des pics anormaux et les qualifier **global** vs **local**.

**Pipeline**

1. Comptage 1–5 min : nouveaux articles/cluster, **sources uniques**, langues, **aire géo dominante** (depuis `cluster_locations`).
2. Score `S = w1*volume + w2*velocity + w3*acceleration + w4*novelty + w5*source_diversity + w6*locality`.
3. Seuils **différenciés** : `τ_global` vs `τ_local` (les évènements très locaux déclenchent à un volume plus faible si corroborés par ≥N sources locales + 1 source tier A si possible).
4. Corroboration : ≥ N **sources distinctes**; pondérer par `trust_tier`.
5. Fusion : si deux clusters explosent et partagent même aire (cosine ≥ 0.9), fusionner avant alerte.
6. Gating LLM : résumé “breaking” seulement si `S >= τ_critical`.

---

## 22) Notifications (push/email) & règles

**Canal push** : **Firebase Cloud Messaging (FCM)** pour Flutter (iOS/Android/Web).

**Flux** : `event_detected` → `rule_match` → `build_payload` → `send_fcm` → `record_delivery`.

**Tables (extrait)**

```sql
create table user_devices (
  id bigserial primary key,
  user_id uuid not null,
  fcm_token text not null,
  platform text check (platform in ('ios','android','web')) not null,
  created_at timestamptz default now()
);

create table subscriptions (
  id bigserial primary key,
  user_id uuid not null,
  kind text check (kind in ('entity','topic','keyword','location')) not null,
  value text not null,
  lang text,
  min_severity text default 'medium',
  quiet_hours int4range,
  created_at timestamptz default now()
);

create table notifications (
  id bigserial primary key,
  user_id uuid not null,
  event_id bigint references events(id) on delete cascade,
  title text,
  body text,
  sent_at timestamptz,
  dedupe_key text,
  channel text check (channel in ('push','email')) not null,
  status text check (status in ('scheduled','sent','failed')) not null default 'scheduled'
);
create unique index on notifications (user_id, dedupe_key);
```

**Règles dynamiques (option)** :

```sql
create table alert_rules (
  id bigserial primary key,
  name text,
  query jsonb,        -- entités/mots-clés/zone
  conditions jsonb,   -- seuils: score, sources uniques, langues
  channels text[] default '{push}',
  is_active boolean default true
);
```

**Bonnes pratiques**

- [ ] **Quiet hours** par utilisateur, time‑zone Europe/Paris.
- [ ] **Dédup**: ne pas renvoyer plusieurs fois le même évènement (`dedupe_key`).
- [ ] **Escalade**: répéter uniquement si score/severity augmente significativement.

---

## 23) Dépendances supplémentaires (crawling/évènements/notifications)

- [ ] SSE côté serveur, BeautifulSoup, extruct (JSON‑LD), orjson.
- [ ] networkx + (optionnel) algos de communautés (python‑louvain).
- [ ] rapidfuzz (fuzzy matching d’entités), reppy (robots.txt).
- [ ] firebase‑admin (FCM), tenacity (retries).
- [ ] Optionnels lourds : hdbscan, scikit‑learn, PostGIS (si géo avancée).

---

## 24) Sécurité, légalité, qualité

- [ ] **robots.txt/ToS** stricts, liste de **sources autorisées** préférable.
- [ ] Pas d’extraits longs d’articles payants ; conserver les **liens**.
- [ ] **Modération**: filtrer contenus choquants (mots‑clés, classif simple) avant résumé.
- [ ] **Transparence**: afficher sources et horodatage UTC + Europe/Paris.
- [ ] **RGPD**: droit à l’effacement (comptes), rétention minimale des tokens FCM.

---

## 25) Coûts & performances (gating)

- [ ] **Batch embeddings** et cache sur `text_hash`.
- [ ] **Chunking adaptatif**: ne vectoriser que le cœur (lead + 2–3 paragraphes) pour le clustering; résumé LLM seulement si **évènement** ou **cluster mature**.
- [ ] **Backpressure**: stop ingestion si files > seuil; prioriser sources clés.

---

## 26) Scheduler (ex. périodicités — sans code)

- [ ] **Chaque minute** : batch `crawl_fetch` par domaine (budgets), monitor frontier.
- [ ] **Toutes les 5 min** : mise à jour `trend_metrics` + détection d’évènements + éventuelle notification.
- [ ] **Toutes les 15 min** : reclustering communautaire (par run active) & refresh sitemaps/sources.
- [ ] **Chaque heure** : compaction/optimisation Meilisearch, purge des files anciennes.
- [ ] **Chaque jour** : purge selon rétention (cf. §29), rapports d’observabilité/coûts, rotation éventuelle des clés/API.

---

## 27) Principes & choix clés (tech + multilingue)

- [ ] **Architecture versionnée** : embeddings multi‑espaces + clustering par "runs" actives ⇒ A/B, rollback, migration IA locale sans casser l’API.
- [ ] **Ingestion par phases** : MVP = RSS/APIs → Phase 2 = sitemaps/scrapers → Phase 3 = crawler complet si ROI.
- [ ] **Simplicité avant tout** : une seule sortie **canonical EN** stockée; variantes locales **à la demande** (cache court) pour UX et coûts maîtrisés.
- [ ] **KG light** (entités, zones) : indispensable pour filtres, abonnements par entité/lieu, et score de **localité**.
- [ ] **Recherche hybride** : plein‑texte (Meili) + sémantique (pgvector) pour pertinence et tolérance aux fautes.
- [ ] **Transparence & biais** : sources visibles, séparation FAITS/ALLÉGATIONS, axes politiques source + biais par article.
- [ ] **Ops** : Celery/Redis (retries, DLQ), SLO clairs, rétention 365 jours, SSE pour temps réel.

## 29) Spécifications non‑fonctionnelles & **rétention**

- [ ] **Rétention par défaut (365 j)** : `raw_html`, `trend_metrics`, logs, notifications; embeddings/clusters conservés jusqu’à renouvellement majeur.
- [ ] **SLO ingestion→cluster** : P50 ≤ 2 min, P95 ≤ 5 min.
- [ ] **SLO évènement→notification** : P50 ≤ 1 min, P95 ≤ 3 min.
- [ ] **Disponibilité API** : ≥ 99.9%/mois.
- [ ] **Débit cible** : 50–100 URLs/min (scalable horizontalement).
- [ ] **Observabilité** : métriques pipeline/LLM/coûts, traces distribuées, journaux auditables.

## 30) Structure de fonctionnement (résumé exécutable)

1. **Ingestion (RSS/APIs)** → 2) **Normalize/dedupe** → 3) **Embed (espace actif)** → 4) **Cluster (run active)** → 5) **Summarize EN + locales (cache)** → 6) **Trend/Event** → 7) **Notify (FCM)** → 8) **Serve API/Stream** → 9) **Personnaliser & classer (For You / Following / Breaking)**.

---

## 31) Personnalisation par intérêts (déclaratif + implicite)

**Objectif** : montrer ce qui **compte** pour l’utilisateur et **masquer le bruit** — sans créer de bulle.

### 31.1 Modèle de données (schémas)

```sql
create table user_interests (
  user_id uuid not null,
  kind text check (kind in ('entity','category','location','source','keyword')) not null,
  value text not null,                 -- id ou slug (ex: 'FR', 'aviation', 'Paris')
  weight real default 1.0,             -- intensité déclarée
  declared boolean default true,       -- vs appris implicitement
  expires_at timestamptz,
  must_include boolean default false,  -- hard-include même si faible engagement
  hard_filter boolean default false,   -- exclure strictement (sauf breaking safety)
  primary key (user_id, kind, value)
);

create table user_feedback (
  user_id uuid not null,
  target_type text check (target_type in ('cluster','article','source')) not null,
  target_id bigint not null,
  signal text check (signal in ('like','hide','dismiss','save','share','open','dwell')) not null,
  value real default 1.0,              -- ex: dwell seconds, like=1, hide=1
  ts timestamptz default now(),
  primary key (user_id, target_type, target_id, signal, ts)
);

create table user_vectors (
  user_id uuid primary key,
  space_id bigint references embedding_spaces(id),
  vector vector(1024),
  updated_at timestamptz default now()
);

create table user_context (
  user_id uuid primary key,
  travelling_area_id bigint,          -- geo_areas.id (opt-in)
  travel_dates daterange,
  relatives_areas bigint[]            -- liste geo_areas.id (opt-in)
);
```

### 31.2 API (ajouts)

- [ ] `GET/POST /user/interests` : gérer intérêts (déclarés, `must_include`, `hard_filter`, échéances).
- [ ] `POST /user/feedback` : like/hide/save/share/open/dwell (agrégation côté backend).
- [ ] `GET/POST /user/context` : zones de voyage/attaches (opt‑in explicite).
- [ ] Flux : `GET /feed/for-you` (classé) ; `GET /feed/following` (déclaratif) ; `GET /feed/breaking` (sévérité).

### 31.3 Politique de ranking (pseudo‑code)

```
score = w_recency*f(age)
      + w_severity*severity
      + w_declared*match(user_interests, cluster)
      + w_geo*geo_proximity(user_context, cluster_locations)
      + w_personal*sim(user_vector, cluster_vector)
      + w_source*trust_tier(source)
      + w_diversity*novelty(category/political_axis)
      - w_fatigue*repetition(topic)

CONTRAINTES:
- MUST_INCLUDE: garantir n items/24h pour (user_interests.must_include=true) et `subscriptions`.
- HARD_FILTER: exclure sauf si event.severity>=critical OU safety (catégorie "public-safety").
- EXPLORATION: ε-greedy/UCB sur un petit pourcentage pour découvrir nouvelles sources/sujets.
- DIVERSITÉ: quotas par catégorie/political_axis pour éviter la bulle.
```

### 31.4 UX & explications

- [ ] Badges **Pourquoi je vois ça ?** (déclaré, proche géographiquement, similaire à vos likes, breaking).
- [ ] Contrôles rapides (Masquer ce sujet, Moins de…, Plus de…)
- [ ] Respect des préférences **déclaratives** même sans likes (Following ≠ For You).

### 31.5 Confidentialité & conformité

- [ ] Contexte (voyages/relatives) **opt‑in** et **éditable** ; usage uniquement pour la personnalisation.
- [ ] Export/suppression des signaux (`user_feedback`) via RGPD.

---

## 32) Évaluation de la personnalisation

**Offline** : NDCG@k, coverage d’intérêts déclarés, diversité catégories/axes, taux de masquage adéquat.
**Online** : CTR, dwell-time, saves, hide rate, regret (remontrée après hide), satisfaction via feedback.
**Canary** : A/B par `ab_tests`/`ab_buckets`.

---

## 33) Scheduler (MAJ personnalis.)

- [ ] **Toutes les 15 min** : mise à jour `user_vectors` pour utilisateurs actifs (incrémental).
- [ ] **Chaque jour** : décadence des poids implicites, expiration `expires_at`, recalibrage des quotas diversité.

---) Structure de fonctionnement (résumé exécutable)

1. **Crawl/ingest** → 2) **Normalize/dedupe** → 3) **Embed (espace actif)** → 4) **Cluster (run active)** → 5) **Summarize EN + locales (cache)** → 6) **Trend/Event** → 7) **Notify (FCM)** → 8) **Serve API/Stream (topics & events)**.

---) Multilingue — design & justification

- [ ] **Embeddings multilingues** : permettent le **clustering cross‑langue** (FR/EN/… sur un même sujet) sans traduction préalable.
- [ ] **Détection de langue** : stockée au niveau article; sert à appliquer stop‑words, stemming, règles de qualité et filtres.
- [ ] **Recherche mixte** : l’utilisateur peut chercher en FR et retrouver des sources EN via similarité sémantique (avec label FR).
- [ ] **Résumé ciblé** : sortie LLM dans la **langue préférée** de l’utilisateur même si sources mixtes; transparence via liste d’URLs originales.
- [ ] **NER/Géocodage** : modèles/lexiques multilingues pour entités; normalisation ISO (personnes, organisations, lieux).
- [ ] **UI/UX** : préférence de langue, choix d’inclure/exclure langues étrangères, avertissement si la synthèse s’appuie majoritairement sur une autre langue.

## 29) Spécifications non‑fonctionnelles (SLO cibles)

- [ ] **Latence ingestion→cluster** : P50 ≤ 2 min, P95 ≤ 5 min.
- [ ] **Latence évènement→notification** : P50 ≤ 1 min (après détection), P95 ≤ 3 min.
- [ ] **Disponibilité API** : ≥ 99.9%/mois (hors maintenances planifiées).
- [ ] **Débit** : 50–100 URLs/min en vitesse de croisière (scalable horizontalement).
- [ ] **Coûts LLM** : budget mensuel borné; gating (résumé uniquement pour clusters matures/évènements).
- [ ] **Conformité** : RGPD (données EU), chiffrement at‑rest (Postgres/Redis) et in‑transit (TLS), rotation secrets.
- [ ] **Observabilité** : métriques clés (erreurs/latences/coûts), traces distribuées, journaux auditables.

## 30) Structure de fonctionnement (résumé exécutable)

1. **Crawl/ingest** → 2) **Normalize/dedupe** → 3) **Embed** → 4) **Cluster** → 5) **Summarize/Bias** → 6) **Trend/Event** → 7) **Notify** → 8) **Serve API/Stream**.

---

## 31) Migration vers clustering/processing IA **natif Python** (sans friction)

**Objectif** : pouvoir passer d’un pipeline IA “as‑a‑service” (embeddings/résumés externes) à un pipeline **on‑prem/OSS** (embeddings, clustering et résumé exécutés dans vos workers Python) sans casser l’API ni les données.

### Principes d’architecture

- [ ] **Ports & Adapters** : définir des interfaces stables (pseudocode) :

  - [ ] `EmbeddingProvider.embed(text) -> vector`
  - [ ] `Clusterer.assign(article_id) -> cluster_id`
  - [ ] `Summarizer.summarize(cluster_id) -> {summary_md, bias_md, timeline_md}`
    Chaque implémentation (Mistral, modèle local…) est interchangeable par **feature flag**.
- [ ] **Double écriture (shadow)** : exécuter un **nouveau provider/clusterer en parallèle** du courant; ne servir à l’app que la version active.
- [ ] **Contrats de données versionnés** : stocker **espace d’embedding** et **run de clustering** pour tracer quelle version a produit chaque résultat.
- [ ] **Reproductibilité** : journaliser modèle, paramètres, seed, commit git, dépendances.

---

## 32) Modèle de données pour le versionnement (embeddings & clustering)

### 32.1 Registre des espaces d’embedding

```sql
create table embedding_spaces (
  id bigserial primary key,
  name text not null,           -- ex: 'mistral-embed', 'e5-large', 'bge-base'
  provider text not null,       -- 'mistral', 'oss-local', ...
  dims int not null,
  version text,
  notes text,
  created_at timestamptz default now(),
  unique(name, version)
);
```

**Stockage des vecteurs — deux stratégies**

- [ ] **A. Table par espace** (recommandée pour dims variées et index optimaux) :

  - [ ] `article_embeddings_<space_slug>(article_id, embedding vector(<dims>))`
  - [ ] L’ID de l’espace est référencé dans la config; index ivfflat par table.
- [ ] **B. Table unique multi‑espaces** (si dims homogènes) :

```sql
create table article_embeddings_multi (
  space_id bigint references embedding_spaces(id),
  article_id bigint references articles(id) on delete cascade,
  embedding vector(1024),
  primary key (space_id, article_id)
);
create index on article_embeddings_multi using ivfflat (embedding vector_cosine_ops);
```

### 32.2 Versionnement du clustering

```sql
create table cluster_runs (
  id bigserial primary key,
  space_id bigint references embedding_spaces(id),
  algo text not null,                 -- 'threshold+communities', 'hdbscan', ...
  params jsonb not null,              -- τ, fenêtre, k, etc.
  started_at timestamptz default now(),
  finished_at timestamptz,
  status text check (status in ('running','complete','failed')),
  is_active boolean default false,
  notes text
);

create table clusters_v (
  id bigserial primary key,
  run_id bigint references cluster_runs(id) on delete cascade,
  label text,
  window_start timestamptz,
  window_end timestamptz,
  created_at timestamptz default now()
);

create table article_cluster_v (
  run_id bigint references cluster_runs(id) on delete cascade,
  cluster_id bigint references clusters_v(id) on delete cascade,
  article_id bigint references articles(id) on delete cascade,
  similarity real,
  primary key (run_id, cluster_id, article_id)
);

-- Vue pour exposer la "run" active sans changer l'API
create view v_clusters_active as
  select c.* from clusters_v c join cluster_runs r on r.id=c.run_id where r.is_active;
create view v_article_cluster_active as
  select ac.* from article_cluster_v ac join cluster_runs r on r.id=ac.run_id where r.is_active;
```

### 32.3 Versionnement des résumés

```sql
create table cluster_summaries_v (
  run_id bigint references cluster_runs(id) on delete cascade,
  cluster_id bigint references clusters_v(id) on delete cascade,
  engine text not null,            -- 'mistral', 'local-llm'
  engine_version text,
  summary_md text,
  bias_md text,
  timeline_md text,
  sources jsonb,
  created_at timestamptz default now(),
  primary key (run_id, cluster_id, engine, engine_version)
);
```

---

## 33) Stratégie de migration (étapes sûres)

1. **Préparer les registres** : créer `embedding_spaces`, `cluster_runs`, tables versionnées `*_v` & vues `v_*_active`.
2. **Backfill embeddings** pour le **nouvel espace** (batch + quotas) sans impacter l’API.
3. **Lancer un cluster_run (shadow)** sur le nouvel espace → remplir `clusters_v`/`article_cluster_v`.
4. **Générer résumés** en parallèle dans `cluster_summaries_v` avec `engine='local-llm'` (ou rester sur Mistral si seul le clustering change).
5. **Évaluer** (voir §34) sur un corpus témoin; ajuster τ/params.
6. **Canary** : marquer `is_active=true` sur le nouveau `run_id` pour **X% des utilisateurs** (via un flag côté API).
7. **Basculer** : set `is_active=true` pour tous; conserver l’ancienne run N jours pour rollback.
8. **Nettoyage** : purge progressive des embeddings obsolètes si coûts de stockage.

---

## 34) Évaluation & qualité (offline + online)

**Offline**

- [ ] **Topic coherence** (PMI/NPMI), **purity** (si labels dispos), taille moyenne des clusters, ratio near‑dup.
- [ ] **Cross‑lingual recall** : proportion d’articles d’autres langues rattachés correctement.
- [ ] **Stabilité** : taux de remappage d’articles entre runs successifs.

**Online**

- [ ] **CTR** sur notifications, **dwell time** par sujet, **feedback utile/biais**.
- [ ] **A/B** : table `ab_tests(user_id, run_id, bucket, started_at, ended_at)`.

**Jeu de vérité** (option)

- [ ] Panel interne + guidelines d’annotation (mêmes sujets / pas mêmes sujets, biais perçu, exhaustivité).

---

## 35) Spécificités infra pour IA native

- [ ] **Workers GPU dédiés** (queue `gpu`) pour embeddings/résumés locaux; batch & quantization pour réduire coût/latence.
- [ ] **Limiteurs** : plafond QPS/TPM par modèle; backpressure sur files.
- [ ] **Cache de features** : ne recalculer un embedding que si `text_hash` change.
- [ ] **Observabilité IA** : temps/token, mémoire GPU, taux d’erreur modèle.
- [ ] **Sécurité** : sandbox pour exécutables tiers, revue des licences modèles/datasets.
