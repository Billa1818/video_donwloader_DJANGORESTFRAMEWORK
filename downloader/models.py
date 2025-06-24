from django.db import models
from django.contrib.auth.models import User
from django.core.validators import URLValidator
import uuid
import os


class Platform(models.Model):
    """Modèle pour les différentes plateformes supportées"""
    PLATFORMS = [
        ('youtube', 'YouTube'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('twitter', 'Twitter/X'),
        ('vimeo', 'Vimeo'),
        ('dailymotion', 'Dailymotion'),
        ('other', 'Autre'),
    ]
    
    name = models.CharField(max_length=50, choices=PLATFORMS, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    base_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Plateforme"
        verbose_name_plural = "Plateformes"
        ordering = ['name']
    
    def __str__(self):
        return self.display_name


class VideoDownload(models.Model):
    """Modèle principal pour les téléchargements de vidéos"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours de traitement'),
        ('completed', 'Terminé'),
        ('failed', 'Échec'),
        ('cancelled', 'Annulé'),
    ]
    
    QUALITY_CHOICES = [
        ('144p', '144p'),
        ('240p', '240p'),
        ('360p', '360p'),
        ('480p', '480p'),
        ('720p', '720p (HD)'),
        ('1080p', '1080p (Full HD)'),
        ('1440p', '1440p (2K)'),
        ('2160p', '2160p (4K)'),
        ('best', 'Meilleure qualité disponible'),
        ('worst', 'Qualité minimale'),
    ]
    
    # Identifiant unique
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # URL de la vidéo source
    source_url = models.URLField(validators=[URLValidator()])
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    
    # Informations sur la vidéo
    title = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    duration = models.PositiveIntegerField(blank=True, null=True, help_text="Durée en secondes")
    thumbnail_url = models.URLField(blank=True, null=True)
    
    # Paramètres de téléchargement
    requested_quality = models.CharField(max_length=20, choices=QUALITY_CHOICES, default='best')
    download_audio_only = models.BooleanField(default=False)
    
    # Statut et progression
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress_percentage = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    # Fichier téléchargé
    file_path = models.FileField(upload_to='downloads/', blank=True, null=True)
    file_size = models.PositiveBigIntegerField(blank=True, null=True, help_text="Taille en bytes")
    actual_quality = models.CharField(max_length=20, blank=True, null=True)
    
    # Métadonnées
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Expiration
    expires_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Téléchargement de vidéo"
        verbose_name_plural = "Téléchargements de vidéos"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['platform', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title or 'Vidéo'} - {self.get_status_display()}"
    
    @property
    def file_size_mb(self):
        """Retourne la taille du fichier en MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None
    
    @property
    def download_url(self):
        """URL de téléchargement du fichier"""
        if self.file_path:
            return self.file_path.url
        return None
    
    def get_filename(self):
        """Génère un nom de fichier sécurisé"""
        if self.file_path:
            return os.path.basename(self.file_path.name)
        return None


class DownloadStatistics(models.Model):
    """Modèle pour les statistiques de téléchargement"""
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    date = models.DateField()
    total_downloads = models.PositiveIntegerField(default=0)
    successful_downloads = models.PositiveIntegerField(default=0)
    failed_downloads = models.PositiveIntegerField(default=0)
    total_size_mb = models.PositiveBigIntegerField(default=0)
    
    class Meta:
        verbose_name = "Statistique de téléchargement"
        verbose_name_plural = "Statistiques de téléchargement"
        unique_together = ['platform', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.platform.display_name} - {self.date}"
    
    @property
    def success_rate(self):
        """Taux de réussite en pourcentage"""
        if self.total_downloads > 0:
            return round((self.successful_downloads / self.total_downloads) * 100, 2)
        return 0


class DownloadHistory(models.Model):
    """Historique des téléchargements pour analytics"""
    download = models.OneToOneField(VideoDownload, on_delete=models.CASCADE)
    
    # Informations techniques
    extractor_used = models.CharField(max_length=100, blank=True, null=True)
    format_id = models.CharField(max_length=50, blank=True, null=True)
    codec = models.CharField(max_length=50, blank=True, null=True)
    bitrate = models.PositiveIntegerField(blank=True, null=True)
    fps = models.PositiveIntegerField(blank=True, null=True)
    
    # Temps de traitement
    processing_time_seconds = models.PositiveIntegerField(blank=True, null=True)
    download_speed_kbps = models.PositiveIntegerField(blank=True, null=True)
    
    # Métadonnées supplémentaires
    uploader = models.CharField(max_length=200, blank=True, null=True)
    upload_date = models.DateField(blank=True, null=True)
    view_count = models.PositiveBigIntegerField(blank=True, null=True)
    like_count = models.PositiveBigIntegerField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Historique de téléchargement"
        verbose_name_plural = "Historiques de téléchargement"
    
    def __str__(self):
        return f"Historique - {self.download.title or 'Vidéo'}"


class SupportedFormat(models.Model):
    """Formats supportés par plateforme"""
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    format_name = models.CharField(max_length=50)  # mp4, webm, m4a, etc.
    mime_type = models.CharField(max_length=100)
    is_video = models.BooleanField(default=True)
    is_audio = models.BooleanField(default=False)
    max_quality = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        verbose_name = "Format supporté"
        verbose_name_plural = "Formats supportés"
        unique_together = ['platform', 'format_name']
        ordering = ['platform__name', 'format_name']
    
    def __str__(self):
        return f"{self.platform.display_name} - {self.format_name}"