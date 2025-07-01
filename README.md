# VIDEO_DOWNLOADER

Téléchargeur de vidéos et d'audios multi-plateformes (YouTube, etc.) avec API REST, interface admin, gestion des tâches asynchrones (Celery), et documentation interactive (Swagger/Redoc).

---

## Fonctionnalités principales
- **Détection automatique de la plateforme** (YouTube, etc.)
- **Liste dynamique des formats disponibles** (vidéo+audio, audio seul, toutes résolutions)
- **Téléchargement asynchrone** (Celery + Redis)
- **Suivi de la progression** (statut, pourcentage)
- **Lien de récupération du fichier**
- **Nettoyage automatique des anciens fichiers**
- **Interface d'administration Django** (ajout, suivi, suppression)
- **Documentation interactive** (Swagger, Redoc)

---

## Prérequis
- Python 3.10+
- [Redis](https://redis.io/) (pour Celery)
- [ffmpeg](https://ffmpeg.org/) (pour fusionner vidéo+audio)
- yt-dlp

---

## Installation rapide

```bash
# Clone le repo
cd VIDEO_DOWNLOADER
python -m venv env
source env/bin/activate
pip install -r requirements.txt

# Installe ffmpeg (Ubuntu/Debian)
sudo apt update && sudo apt install -y ffmpeg

# Installe Redis (si besoin)
sudo apt install redis-server
sudo service redis-server start

# (Optionnel) Copie le .env fourni et adapte-le
cp .env.example .env

# Applique les migrations
python manage.py migrate

# Lance le serveur Django
python manage.py runserver

# Lance le worker Celery (dans un autre terminal)
celery -A VIDEO_DOWNLOADER worker --loglevel=info
```

---

## Endpoints principaux

- **Valider une URL** : `POST /api/validate-url/`
- **Lister les formats** : `POST /api/formats/`
- **Créer un téléchargement** : `POST /api/downloads/create/`
- **Suivre un téléchargement** : `GET /api/downloads/{id}/status/`
- **Récupérer le fichier** : `GET /downloads/<filename>`
- **Supprimer un téléchargement** : `DELETE /api/downloads/{id}/delete/`

---

## Documentation interactive
- **Swagger UI** : [http://127.0.0.1:8000/swagger/](http://127.0.0.1:8000/swagger/)
- **Redoc** : [http://127.0.0.1:8000/redoc/](http://127.0.0.1:8000/redoc/)

---

## Utilisation côté front-end
1. L'utilisateur saisit l'URL de la vidéo.
2. Le front appelle `/api/validate-url/` puis `/api/formats/` pour afficher les formats disponibles (vidéo+audio, audio seul).
3. L'utilisateur choisit un format et lance le téléchargement via `/api/downloads/create/`.
4. Le front suit la progression via `/api/downloads/{id}/status/`.
5. Quand le téléchargement est prêt, le front propose le lien de récupération.

---

## Administration
- Accès à l'admin Django : [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
- Ajout/suivi/suppression de téléchargements, gestion des plateformes, etc.

---

## Personnalisation
- Pour ajouter d'autres plateformes, formats ou logiques, voir le dossier `downloader/`.
- Pour modifier la fréquence de nettoyage automatique, voir la config Celery dans `VIDEO_DOWNLOADER/celery.py`.
