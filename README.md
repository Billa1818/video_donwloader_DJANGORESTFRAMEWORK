# Video Downloader API

Une API REST complète pour télécharger des vidéos depuis différentes plateformes (YouTube, Vimeo, etc.) avec gestion des tâches asynchrones via Celery.

## 🚀 Fonctionnalités

- **Multi-plateformes** : Support pour YouTube, Vimeo, et autres plateformes
- **Téléchargements asynchrones** : Gestion des tâches avec Celery et Redis
- **Formats multiples** : Vidéo et audio, différentes qualités
- **API REST complète** : Endpoints pour tous les besoins
- **Documentation Swagger** : Interface interactive pour tester l'API
- **Statistiques** : Suivi des téléchargements et performances
- **Validation d'URL** : Vérification avant téléchargement
- **Téléchargements en lot** : Support pour plusieurs URLs simultanément

## 📋 Prérequis

- Python 3.8+
- Redis (pour Celery)
- FFmpeg (pour le traitement vidéo)

## 🛠️ Installation

1. **Cloner le projet**
```bash
git clone <repository-url>
cd VIDEO_DOWNLOADER
```

2. **Créer un environnement virtuel**
```bash
python -m venv env
source env/bin/activate  # Linux/Mac
# ou
env\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer la base de données**
```bash
python manage.py migrate
```

5. **Créer un superutilisateur (optionnel)**
```bash
python manage.py createsuperuser
```

6. **Lancer Redis** (nécessaire pour Celery)
```bash
redis-server
```

7. **Lancer Celery** (dans un nouveau terminal)
```bash
celery -A VIDEO_DOWNLOADER worker -l info
```

8. **Lancer le serveur Django**
```bash
python manage.py runserver
```

## 📚 Documentation de l'API

### Base URL
```
http://localhost:8000/api/
```

### Documentation Swagger
```
http://localhost:8000/swagger/
```

---

## 🔗 Endpoints de l'API

### 1. Plateformes

#### GET `/api/platforms/`
Récupère la liste de toutes les plateformes supportées.

**Réponse :**
```json
[
  {
    "id": 1,
    "name": "youtube",
    "display_name": "YouTube",
    "base_url": "https://www.youtube.com",
    "is_active": true
  }
]
```

---

### 2. Formats Supportés

#### GET `/api/formats/`
Récupère la liste des formats supportés par plateforme.

**Paramètres de requête :**
- `platform` (int) : ID de la plateforme
- `is_video` (bool) : Filtrer par format vidéo
- `is_audio` (bool) : Filtrer par format audio

**Réponse :**
```json
[
  {
    "id": 1,
    "platform": 1,
    "format_code": "best",
    "display_name": "Meilleure qualité",
    "is_video": true,
    "is_audio": false,
    "is_active": true
  }
]
```

---

### 3. Téléchargements

#### GET `/api/downloads/`
Récupère la liste des téléchargements avec filtres et pagination.

**Paramètres de requête :**
- `status` (string) : Filtrer par statut (`pending`, `processing`, `completed`, `failed`, `cancelled`)
- `platform` (int) : ID de la plateforme
- `download_audio_only` (bool) : Filtrer par type de téléchargement
- `search` (string) : Rechercher dans le titre ou l'URL
- `ordering` (string) : Trier par champ (`created_at`, `-created_at`, `completed_at`, `-completed_at`, `file_size`, `-file_size`)
- `page` (int) : Numéro de page
- `page_size` (int) : Taille de page (max 100)

**Réponse :**
```json
{
  "count": 10,
  "next": "http://localhost:8000/api/downloads/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "title": "Titre de la vidéo",
      "source_url": "https://www.youtube.com/watch?v=...",
      "status": "completed",
      "platform": {
        "id": 1,
        "name": "youtube",
        "display_name": "YouTube"
      },
      "file_path": "/downloads/video.mp4",
      "file_size": 52428800,
      "duration_seconds": 180,
      "created_at": "2024-01-01T12:00:00Z",
      "completed_at": "2024-01-01T12:05:00Z"
    }
  ]
}
```

#### POST `/api/downloads/create/`
Crée un nouveau téléchargement de vidéo.

**Corps de la requête :**
```json
{
  "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "requested_quality": "best",
  "download_audio_only": false
}
```

**Réponse :**
```json
{
  "id": "uuid",
  "title": "Titre de la vidéo",
  "source_url": "https://www.youtube.com/watch?v=...",
  "status": "pending",
  "platform": {
    "id": 1,
    "name": "youtube",
    "display_name": "YouTube"
  },
  "requested_quality": "best",
  "download_audio_only": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### GET `/api/downloads/{id}/`
Récupère les détails complets d'un téléchargement spécifique.

**Réponse :**
```json
{
  "id": "uuid",
  "title": "Titre de la vidéo",
  "source_url": "https://www.youtube.com/watch?v=...",
  "status": "completed",
  "platform": {
    "id": 1,
    "name": "youtube",
    "display_name": "YouTube"
  },
  "file_path": "/downloads/video.mp4",
  "file_size": 52428800,
  "duration_seconds": 180,
  "requested_quality": "best",
  "download_audio_only": false,
  "error_message": null,
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:05:00Z"
}
```

#### GET `/api/downloads/{id}/status/`
Récupère le statut actuel d'un téléchargement (idéal pour le polling).

**Réponse :**
```json
{
  "id": "uuid",
  "status": "processing",
  "progress_percentage": 45,
  "error_message": null
}
```

#### DELETE `/api/downloads/{id}/delete/`
Supprime un téléchargement et son fichier associé.

**Réponse :** 204 No Content

#### POST `/api/downloads/{id}/cancel/`
Annule un téléchargement en cours.

**Réponse :**
```json
{
  "message": "Téléchargement annulé avec succès",
  "download_id": "uuid"
}
```

---

### 4. Validation d'URL

#### POST `/api/validate-url/`
Valide une URL avant téléchargement et détecte la plateforme.

**Corps de la requête :**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Réponse :**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "is_valid": true,
  "platform": "youtube",
  "platform_display": "YouTube",
  "supported_qualities": ["best", "worst", "720p", "480p"]
}
```

---

### 5. Téléchargements en Lot

#### POST `/api/bulk-download/`
Crée plusieurs téléchargements en lot.

**Corps de la requête :**
```json
{
  "urls": [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=Zi_XLOBDo_Y"
  ],
  "requested_quality": "best",
  "download_audio_only": false
}
```

**Réponse :**
```json
{
  "message": "Téléchargements créés avec succès",
  "downloads": [
    {
      "id": "uuid1",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "status": "pending"
    },
    {
      "id": "uuid2",
      "url": "https://www.youtube.com/watch?v=Zi_XLOBDo_Y",
      "status": "pending"
    }
  ]
}
```

---

### 6. Historique

#### GET `/api/history/`
Récupère l'historique des téléchargements avec métadonnées techniques.

**Paramètres de requête :**
- `download__platform` (int) : ID de la plateforme
- `download__status` (string) : Statut du téléchargement
- `ordering` (string) : Trier par champ

**Réponse :**
```json
{
  "count": 10,
  "next": "http://localhost:8000/api/history/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "download": {
        "id": "uuid",
        "title": "Titre de la vidéo",
        "status": "completed"
      },
      "processing_time_seconds": 300,
      "download_speed_kbps": 1024,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

---

### 7. Statistiques

#### GET `/api/statistics/`
Récupère les statistiques de téléchargement par jour et plateforme.

**Paramètres de requête :**
- `platform` (int) : ID de la plateforme
- `date` (string) : Date (YYYY-MM-DD)
- `ordering` (string) : Trier par champ

**Réponse :**
```json
{
  "count": 10,
  "next": "http://localhost:8000/api/statistics/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "platform": {
        "id": 1,
        "name": "youtube",
        "display_name": "YouTube"
      },
      "date": "2024-01-01",
      "total_downloads": 25,
      "successful_downloads": 23,
      "failed_downloads": 2,
      "success_rate": 0.92,
      "total_file_size_mb": 1024.5
    }
  ]
}
```

#### GET `/api/download-stats/`
Récupère les statistiques agrégées de téléchargement.

**Réponse :**
```json
{
  "total_downloads": 150,
  "successful_downloads": 142,
  "failed_downloads": 8,
  "success_rate": 0.947,
  "total_file_size_mb": 6144.2,
  "avg_file_size_mb": 40.96,
  "downloads_today": 12,
  "downloads_this_week": 45,
  "downloads_this_month": 150
}
```

#### GET `/api/platform-stats/`
Récupère les statistiques par plateforme.

**Réponse :**
```json
[
  {
    "platform_name": "YouTube",
    "total_downloads": 100,
    "success_rate": 0.95,
    "avg_file_size_mb": 45.2
  },
  {
    "platform_name": "Vimeo",
    "total_downloads": 50,
    "success_rate": 0.92,
    "avg_file_size_mb": 35.8
  }
]
```

---

### 8. Santé du Système

#### GET `/api/health/`
Vérifie l'état de santé de l'API et des services.

**Réponse :**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "database": "connected",
  "celery": "running"
}
```

---

## 🔧 Configuration

### Variables d'environnement

Créez un fichier `.env` à la racine du projet :

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Configuration Celery

Le projet utilise Celery pour les tâches asynchrones. Les tâches sont configurées dans `VIDEO_DOWNLOADER/celery.py`.

### Tâches périodiques

- **Nettoyage automatique** : Supprime les fichiers téléchargés de plus de 30 jours
- **Mise à jour des statistiques** : Met à jour les statistiques quotidiennes

---

## 🧪 Tests

### Tests unitaires
```bash
python manage.py test
```

### Tests d'intégration
```bash
python manage.py test downloader.tests
```

---

## 📊 Monitoring

### Logs
Les logs sont configurés dans `settings.py` et peuvent être consultés dans :
- Console Django
- Fichiers de log (si configurés)

### Métriques
- Statistiques de téléchargement via l'API
- Historique des performances
- Taux de succès par plateforme

---

## 🚀 Déploiement

### Production
1. Configurer les variables d'environnement
2. Utiliser un serveur WSGI (Gunicorn)
3. Configurer un reverse proxy (Nginx)
4. Utiliser Redis en production
5. Configurer les tâches Celery avec Supervisor

### Docker (optionnel)
```bash
docker-compose up -d
```

---

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## 🆘 Support

Pour toute question ou problème :
- Ouvrir une issue sur GitHub
- Consulter la documentation Swagger : `http://localhost:8000/swagger/`
- Vérifier les logs de l'application
