# Backend SBV - API Documentation

## 🚀 Quick Start

### Démarrer le serveur API

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Le serveur sera accessible sur `http://localhost:8000`

### Documentation interactive

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 Endpoints Disponibles

### Health Check

**GET** `/health`

Vérification de l'état du serveur.

**Réponse:**
```json
{
  "status": "healthy"
}
```

### Liste des Topics (Clusters)

**GET** `/api/v1/topics`

Récupère la liste paginée des clusters actifs.

**Paramètres de requête:**
- `skip` (int, optionnel): Nombre d'éléments à ignorer (défaut: 0)
- `limit` (int, optionnel): Nombre maximum d'éléments à retourner (défaut: 20, max: 100)

**Réponse:**
```json
{
  "total": 5,
  "topics": [
    {
      "id": 1,
      "run_id": 1,
      "label": "Tech News",
      "window_start": "2025-09-30T10:00:00Z",
      "window_end": "2025-09-30T18:00:00Z",
      "created_at": "2025-09-30T10:00:00Z",
      "article_count": 12
    }
  ],
  "skip": 0,
  "limit": 20
}
```

### Détail d'un Topic

**GET** `/api/v1/topics/{cluster_id}`

Récupère les détails d'un cluster spécifique avec tous ses articles.

**Paramètres de chemin:**
- `cluster_id` (int): ID du cluster

**Réponse:**
```json
{
  "id": 1,
  "run_id": 1,
  "label": "Tech News",
  "window_start": "2025-09-30T10:00:00Z",
  "window_end": "2025-09-30T18:00:00Z",
  "created_at": "2025-09-30T10:00:00Z",
  "articles": [
    {
      "id": 42,
      "title": "Breaking Tech News",
      "url": "https://example.com/article",
      "source_id": 1,
      "published_at": "2025-09-30T12:00:00Z",
      "lang": "en",
      "similarity": 0.92
    }
  ]
}
```

**Erreurs:**
- `404 Not Found`: Le cluster n'existe pas ou n'est pas actif

## 🏗️ Architecture

### Vues SQL Actives

L'API utilise deux vues SQL pour accéder aux clusters actifs:

- **v_clusters_active**: Clusters de la run active
- **v_article_cluster_active**: Associations article-cluster de la run active

Ces vues sont créées par la migration `0fa290b0f956_create_active_cluster_views.py`

### Modèles Pydantic

Les réponses API sont validées avec Pydantic:

- `ClusterListItem`: Item de liste avec compteur d'articles
- `ClusterDetail`: Détails complets avec liste d'articles
- `ArticleInCluster`: Information d'article dans un cluster
- `TopicsListResponse`: Réponse de liste paginée

## 🔧 Développement

### Tester l'API manuellement

```bash
# Health check
curl http://localhost:8000/health

# Liste des topics
curl http://localhost:8000/api/v1/topics

# Détail d'un topic
curl http://localhost:8000/api/v1/topics/1

# Avec pagination
curl "http://localhost:8000/api/v1/topics?skip=0&limit=10"
```

### Prochaines étapes

1. ✅ Vues SQL actives créées
2. ✅ Endpoints de base implémentés
3. 🔲 Ajouter endpoint de recherche
4. 🔲 Ajouter streaming en temps réel (SSE)
5. 🔲 Ajouter authentification
6. 🔲 Ajouter métriques Prometheus
