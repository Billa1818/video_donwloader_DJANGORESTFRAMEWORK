import os
import yt_dlp
import logging
from celery import Celery, shared_task
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from datetime import datetime, timedelta
from .models import VideoDownload, DownloadHistory, DownloadStatistics, Platform

# Configuration du logger
logger = logging.getLogger(__name__)

# Configuration Celery
# app = Celery('video_downloader')
# app.config_from_object('django.conf:settings', namespace='CELERY')
# app.autodiscover_tasks()


class VideoDownloadProgress:
    """Classe pour suivre la progression du téléchargement"""
    
    def __init__(self, download_id):
        self.download_id = download_id
        self.start_time = None
    
    def progress_hook(self, d):
        """Hook de progression pour yt-dlp"""
        try:
            download = VideoDownload.objects.get(id=self.download_id)
            
            if d['status'] == 'downloading':
                if self.start_time is None:
                    self.start_time = timezone.now()
                    download.started_at = self.start_time
                
                # Calcul du pourcentage
                if 'total_bytes' in d and d['total_bytes']:
                    downloaded = d.get('downloaded_bytes', 0)
                    progress = int((downloaded / d['total_bytes']) * 100)
                    download.progress_percentage = min(progress, 99)  # Max 99% pendant le téléchargement
                elif '_percent_str' in d:
                    # Extraction du pourcentage depuis la chaîne
                    percent_str = d['_percent_str'].strip().replace('%', '')
                    try:
                        progress = float(percent_str)
                        download.progress_percentage = int(min(progress, 99))
                    except:
                        pass
                
                download.status = 'processing'
                download.save(update_fields=['status', 'progress_percentage', 'started_at'])
            
            elif d['status'] == 'finished':
                download.progress_percentage = 100
                download.save(update_fields=['progress_percentage'])
                
        except Exception as e:
            logger.error(f"Erreur dans progress_hook: {e}")


@shared_task(bind=True, max_retries=3)
def download_video_task(self, download_id):
    """Tâche Celery pour télécharger une vidéo"""
    logger.info(f"Début du téléchargement pour l'ID: {download_id}")
    
    try:
        download = VideoDownload.objects.get(id=download_id)
        download.status = 'processing'
        download.started_at = timezone.now()
        download.save()
        
        # Configuration yt-dlp
        progress_tracker = VideoDownloadProgress(download_id)
        
        # Dossier de téléchargement
        download_dir = os.path.join(settings.MEDIA_ROOT, 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        
        # Configuration des options yt-dlp
        ydl_opts = {
            'outtmpl': os.path.join(download_dir, f'{download_id}_%(title)s.%(ext)s'),
            'progress_hooks': [progress_tracker.progress_hook],
            'no_warnings': False,
            'extractaudio': download.download_audio_only,
            'audioformat': 'mp3' if download.download_audio_only else None,
            'ignoreerrors': False,
            'no_check_certificate': True,
        }
        
        # Configuration de la qualité
        if download.requested_quality == 'best':
            if download.download_audio_only:
                ydl_opts['format'] = 'bestaudio/best'
            else:
                ydl_opts['format'] = 'best[height<=1080]'
        elif download.requested_quality == 'worst':
            ydl_opts['format'] = 'worst'
        else:
            # Qualité spécifique (720p, 480p, etc.)
            height = download.requested_quality.replace('p', '')
            if download.download_audio_only:
                ydl_opts['format'] = 'bestaudio/best'
            else:
                ydl_opts['format'] = f'best[height<={height}]'
        
        # Téléchargement avec yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extraction des informations
                info = ydl.extract_info(download.source_url, download=False)
                
                # Mise à jour des métadonnées
                download.title = info.get('title', '')[:500]  # Limite à 500 caractères
                download.description = info.get('description', '')[:1000] if info.get('description') else ''
                download.duration = info.get('duration')
                download.thumbnail_url = info.get('thumbnail', '')
                download.save()
                
                # Téléchargement effectif
                ydl.download([download.source_url])
                
                # Recherche du fichier téléchargé
                downloaded_file = None
                for file in os.listdir(download_dir):
                    if file.startswith(str(download_id)):
                        downloaded_file = os.path.join(download_dir, file)
                        break
                
                if downloaded_file and os.path.exists(downloaded_file):
                    # Mise à jour de l'objet download
                    file_size = os.path.getsize(downloaded_file)
                    relative_path = os.path.relpath(downloaded_file, settings.MEDIA_ROOT)
                    
                    download.file_path = relative_path
                    download.file_size = file_size
                    download.actual_quality = info.get('height', download.requested_quality)
                    download.status = 'completed'
                    download.completed_at = timezone.now()
                    download.progress_percentage = 100
                    download.save()
                    
                    # Créer l'historique
                    create_download_history(download, info, progress_tracker.start_time)
                    
                    # Mettre à jour les statistiques
                    update_download_statistics(download, success=True)
                    
                    logger.info(f"Téléchargement terminé avec succès: {download_id}")
                    
                else:
                    raise Exception("Fichier téléchargé non trouvé")
                    
            except Exception as e:
                logger.error(f"Erreur yt-dlp pour {download_id}: {e}")
                raise e
                
    except VideoDownload.DoesNotExist:
        logger.error(f"VideoDownload {download_id} non trouvé")
        return f"VideoDownload {download_id} non trouvé"
        
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement {download_id}: {e}")
        
        try:
            download = VideoDownload.objects.get(id=download_id)
            download.status = 'failed'
            download.error_message = str(e)[:500]
            download.completed_at = timezone.now()
            download.save()
            
            # Mettre à jour les statistiques d'échec
            update_download_statistics(download, success=False)
            
        except VideoDownload.DoesNotExist:
            pass
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retry {self.request.retries + 1}/{self.max_retries} pour {download_id}")
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=e)
        
        return f"Échec définitif du téléchargement {download_id}: {e}"
    
    return f"Téléchargement terminé: {download_id}"


@shared_task
def download_bulk_videos_task(download_ids):
    """Tâche pour télécharger plusieurs vidéos en parallèle"""
    logger.info(f"Début du téléchargement en lot pour {len(download_ids)} vidéos")
    
    results = []
    for download_id in download_ids:
        try:
            # Lancer chaque téléchargement individuellement
            result = download_video_task.delay(download_id)
            results.append({
                'download_id': download_id,
                'task_id': result.id,
                'status': 'started'
            })
        except Exception as e:
            logger.error(f"Erreur lors du lancement du téléchargement {download_id}: {e}")
            results.append({
                'download_id': download_id,
                'task_id': None,
                'status': 'failed',
                'error': str(e)
            })
    
    return results


def create_download_history(download, info, start_time):
    """Créer l'historique du téléchargement"""
    try:
        processing_time = None
        if start_time and download.completed_at:
            processing_time = int((download.completed_at - start_time).total_seconds())
        
        # Calcul de la vitesse de téléchargement
        download_speed = None
        if processing_time and download.file_size:
            speed_bps = download.file_size / processing_time  # bytes per second
            download_speed = int(speed_bps / 1024 * 8)  # Kbps
        
        DownloadHistory.objects.create(
            download=download,
            extractor_used=info.get('extractor', 'yt-dlp'),
            format_id=info.get('format_id', ''),
            codec=info.get('vcodec', ''),
            bitrate=info.get('tbr'),
            fps=info.get('fps'),
            processing_time_seconds=processing_time,
            download_speed_kbps=download_speed,
            uploader=info.get('uploader', '')[:200],
            upload_date=parse_upload_date(info.get('upload_date')),
            view_count=info.get('view_count'),
            like_count=info.get('like_count')
        )
        
        logger.info(f"Historique créé pour le téléchargement {download.id}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'historique: {e}")


def parse_upload_date(date_str):
    """Parse la date d'upload depuis yt-dlp"""
    if not date_str:
        return None
    
    try:
        # Format: YYYYMMDD
        if len(date_str) == 8:
            return datetime.strptime(date_str, '%Y%m%d').date()
    except:
        pass
    
    return None


def update_download_statistics(download, success=True):
    """Mettre à jour les statistiques de téléchargement"""
    try:
        today = timezone.now().date()
        stats, created = DownloadStatistics.objects.get_or_create(
            platform=download.platform,
            date=today,
            defaults={
                'total_downloads': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'total_size_mb': 0
            }
        )
        
        stats.total_downloads += 1
        
        if success:
            stats.successful_downloads += 1
            if download.file_size:
                stats.total_size_mb += int(download.file_size / (1024 * 1024))
        else:
            stats.failed_downloads += 1
        
        stats.save()
        
        logger.info(f"Statistiques mises à jour pour {download.platform.display_name}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des statistiques: {e}")


@shared_task
def cleanup_old_downloads():
    """Tâche de nettoyage des anciens téléchargements"""
    logger.info("Début du nettoyage des anciens téléchargements")
    
    # Supprimer les téléchargements expirés
    expired_downloads = VideoDownload.objects.filter(
        expires_at__lt=timezone.now(),
        status='completed'
    )
    
    deleted_count = 0
    for download in expired_downloads:
        try:
            # Supprimer le fichier physique
            if download.file_path:
                download.file_path.delete()
            
            # Supprimer l'objet
            download.delete()
            deleted_count += 1
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de {download.id}: {e}")
    
    # Supprimer les téléchargements échoués anciens (plus de 7 jours)
    old_failed = VideoDownload.objects.filter(
        status='failed',
        created_at__lt=timezone.now() - timedelta(days=7)
    )
    
    failed_deleted = old_failed.count()
    old_failed.delete()
    
    logger.info(f"Nettoyage terminé: {deleted_count} téléchargements expirés, {failed_deleted} échecs anciens supprimés")
    
    return f"Supprimé: {deleted_count + failed_deleted} éléments"


@shared_task
def update_daily_statistics():
    """Tâche pour calculer les statistiques quotidiennes"""
    logger.info("Mise à jour des statistiques quotidiennes")
    
    yesterday = (timezone.now() - timedelta(days=1)).date()
    
    platforms = Platform.objects.all()
    
    for platform in platforms:
        downloads = VideoDownload.objects.filter(
            platform=platform,
            created_at__date=yesterday
        )
        
        if downloads.exists():
            total = downloads.count()
            successful = downloads.filter(status='completed').count()
            failed = downloads.filter(status='failed').count()
            
            total_size_bytes = downloads.filter(
                status='completed'
            ).aggregate(total=models.Sum('file_size'))['total'] or 0
            
            total_size_mb = int(total_size_bytes / (1024 * 1024))
            
            DownloadStatistics.objects.update_or_create(
                platform=platform,
                date=yesterday,
                defaults={
                    'total_downloads': total,
                    'successful_downloads': successful,
                    'failed_downloads': failed,
                    'total_size_mb': total_size_mb
                }
            )
    
    logger.info("Statistiques quotidiennes mises à jour")
    return f"Statistiques mises à jour pour {platforms.count()} plateformes"